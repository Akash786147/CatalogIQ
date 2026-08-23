# 01 — Architecture

Seven stages. The LLM appears in three of them, always inside a constraint, and
**never** writes a description.

```
 input.csv (6 cols)
      │
      ▼
 ┌─ 1 ─────────────┐  row → classpath + attribute schema
 │  CLASSIFY       │  deterministic router → embedding shortlist → LLM pick
 └────────┬────────┘
          ▼
 ┌─ 2 ─────────────┐  "40W Led Med 27k 2pk" → typed key/value pairs
 │  PARSE          │  template INDUCED per (manufacturer × classpath) family
 └────────┬────────┘
          ▼
 ┌─ 3 ─────────────┐  gap-fill only, in strict source order:
 │  ENRICH         │  3a consensus → 3b manufacturer-doc RAG → 3c null+flag
 └────────┬────────┘
          ▼
 ┌─ 4 ─────────────┐  UOM · fractions · LOV conformance · outliers · contradiction
 │  VALIDATE       │  each check can downgrade confidence or void a value
 └────────┬────────┘
          ▼
 ┌─ 5 ─────────────┐  NO LLM. Template functions over the validated fact layer.
 │  COMPOSE        │  all five descriptions from one shared set of facts
 └────────┬────────┘
          ▼
 ┌─ 6 ─────────────┐  252-col CSV/XLSX  +  parallel provenance file
 │  EMIT           │  + the review queue: "918 clean, 82 need you"
 └────────┬────────┘
          ▼
 ┌─ 7 ─────────────┐  a reviewer edit is stored as a RULE, not a cell patch
 │  PROPAGATE      │  → "applied to 55 rows, 3 now need re-review"
 └─────────────────┘
```

---

## Stage 1 — Classify

**Job:** row → `Classpath` (e.g. `Appliances & Consumer Electronics>Kitchen
Appliances>Built-In Dishwashers`) plus `Dept`/`Class`/`Fine`.

Two-stage, cheap-first:

- **Stage A — deterministic router.** `Part_Manuf` + keyword signature resolves
  ~70% of rows with **zero model calls**. `Phillips Lighting (5831)` + `Led` in
  the description is not ambiguous.
- **Stage B — LLM pick.** For the rest, retrieve the ~10 nearest classpaths by
  embedding similarity, then have the model choose one. Small candidate set,
  small prompt, high accuracy — never "pick from 400."

**Output is not just a label.** It is the classpath *and its attribute schema* —
the permitted `ATTRIBUTE_LABEL` list and the permitted values for each.
Everything downstream is constrained by this object. This is the step-back move:
decide *what class of thing this is* before extracting anything, so the model is
working through a short checklist for bulbs instead of staring at 250 empty
boxes. It cannot invent a "wash cycle" field for a light bulb, because that
question was never on the list.

> Ground truth confirms the schema is fixed per classpath: both dishwasher rows
> emit `ATTRIBUTE_LABEL 1..15` in identical order, with blank `ATTRIBUTE_VALUE`
> where the fact is unknown. **The labels are the checklist; the blanks are the
> honest gaps.**

`app/pipeline/classify.py` · `app/core/taxonomy.py`

---

## Stage 2 — Parse (the learned abbreviation grammar)

**Job:** `40W Led Med 27k 2pk` → `{Wattage: 40 W, Lamp Type: LED, Base: Medium,
Color Temperature: 2700 K, Package Quantity: 2}`

This is the part the brief explicitly says **must not be hardcoded**. Three
passes:

**Pass 1 — tokenise and type.** Split into number-unit pairs (`40W`, `2pk`),
alphanumeric codes (`573352`), and word tokens (`Led`, `Med`).

**Pass 2 — mine the family.** Group rows by `Part_Manuf` × classpath. Across the
111 Philips rows, compute positional and co-occurrence statistics: which token
shapes appear at which position, which vary, which are constant. `27k` varies
across rows in a slot that always holds `<digits>k` → that is a **variable
field**, not boilerplate. This yields candidate slots with no dictionary.

**Pass 3 — name the slots.** **One LLM call per family, not per row.** Show the
model 20 sample rows, the mined slot structure, and the category's attribute
schema; it returns a reusable parse template:

```
slot_2: <int>W   → Wattage              (UOM: W)
slot_4: <int>k   → Color Temperature    (UOM: K, ×100)
slot_5: <int>pk  → Package Quantity
```

The template then runs **deterministically** across all 111 rows. One model call
amortised over a hundred rows — this is why cost per 1,000 SKUs is low enough to
put on a slide.

**Generalisation proof:** hold out an entire manufacturer, induce templates
fresh, measure accuracy. That is the answer to "must handle unseen field
combinations."

`app/pipeline/parse.py` · `app/pipeline/template_induction.py`

---

## Stage 3 — Enrich (gap-fill only, in source order)

**Hard rule: enrichment only ever fills empty cells. Input values are
immutable.** Nothing already present is overwritten.

**3a — Cross-row consensus.** Block on `Part_Manuf` + normalised part-number
prefix, then similarity-cluster into part families. Aggregate attribute values
across members; where ≥N siblings agree and **no** member disagrees, propagate
to sparse members. Provenance records the contributing SKUs. Pure computation —
zero model calls. This is the sleeper feature: it visibly improves rows where a
per-row LLM has nothing to work with, and almost nobody else will build it.

**3b — Manufacturer-document RAG.** Spec sheets chunked and embedded, filtered
by manufacturer + part number at query time. Retrieved chunks go to the model
with a strict instruction: *extract only what this chunk states, return the
source URL, return null otherwise.* A **domain allowlist enforces the sourcing
rule at the retrieval layer** — marketplaces are blocked by code, not by prompt.

**3c — Nothing.** `null` + flag. This is the step everyone else skips, and it is
exactly why their output can't be trusted.

`app/pipeline/consensus.py` · `app/pipeline/retrieve.py`

---

## Stage 4 — Validate

A chain; each check can downgrade confidence or void a value outright.

| Check | Implementation |
|---|---|
| UOM normalisation | Approved abbreviation table; enforce `number␣unit` (`24in` → `24 in`) |
| Decimal → fraction | Exact table 1/64–63/64 + mixed numbers: `50.25 in` → `50-1/4 in`. Tradespeople search in fractions. |
| Vocabulary conformance | Value must exist in the LOV for that classpath. Near-misses go through fuzzy match with a threshold — **below threshold, reject; never snap.** |
| Statistical outlier | Fit the observed distribution per family × attribute **from the corpus at runtime**. A 4000 W bulb gets flagged. Ranges are never hardcoded. |
| Cross-field contradiction | Small rule set + one LLM plausibility pass on assembled records only |
| Entity resolution | `Part_Manuf` → `MANUFACTURER_NAME` / `BRAND_NAME` via lookup + fuzzy match against the approved manufacturer list, preserving exact casing and ®/™ |

`app/pipeline/validate.py` · `app/core/units.py` · `app/core/entities.py`

---

## Stage 5 — Compose (no LLM)

Template functions over the validated fact layer. Field order comes from the
category schema, so it is **data-driven rather than per-category code**.

`INVOICE_DESC` (≤40 chars, uppercase) is a constrained compression: tokens carry
priority weights from the schema, and a greedy loop drops the lowest-priority
token until the string fits, applying approved abbreviations first. Deterministic
and always compliant — **a length assertion in the test suite, not a hope.**

Because all five descriptions read the same fact layer, mutual consistency is
structural. Exact formulas, reverse-engineered from ground truth, are in
[03-composition-rules.md](03-composition-rules.md).

`app/pipeline/compose.py`

---

## Stage 6 — Provenance and confidence

Internally each cell is an object, not a string:

```json
{
  "value": "2700",
  "uom": "K",
  "state": "PARSED",
  "confidence": 0.96,
  "evidence": { "span": [18, 21], "source": "Part_Desc" },
  "reason": "Matched slot_4 of the Philips LED template"
}
```

Confidence composes parse-template fit, vocabulary match strength, consensus
agreement ratio and retrieval score — then is **calibrated on the labelled rows
(isotonic regression)** so that 0.9 actually means 90% correct. That calibration
curve is a slide.

Two writers serialise the same objects: the 252-column CSV/XLSX (values only,
headers untouched) and a parallel provenance file of identical shape.

`app/core/cell.py` · `app/io/writers.py`

---

## Stage 7 — Correction propagation

A reviewer edit is stored as a **rule**, not a cell patch:

```json
{ "scope": "Part_Manuf == 'Black & Decker/dewlt (2585)'",
  "field": "MANUFACTURER_NAME",
  "value": "Stanley Black & Decker, Inc." }
```

Re-run the rule set over the batch, report affected rows, mark downstream
composed fields dirty and recompose them. That is why one fix reports **"applied
to 55 rows, 3 now need re-review."**

The reviewer gets *faster* as they go instead of grinding the same mistake 55
times. This is the demo moment — it is the only part of any submission that
looks like software a company would deploy.

`app/pipeline/rules.py`

---

## Execution

Async worker pool over rows, batched model calls, checkpointed to SQLite so a
failed row doesn't kill a run and a batch can resume. Aggressive caching: parse
templates per family, retrieval per part number, classification per
manufacturer + signature. **Most rows complete with zero model calls** after the
first few in their family.

## Stack

| Layer | Choice |
|---|---|
| Pipeline & API | Python 3.11, FastAPI, Pydantic v2 |
| LLM | Claude (`claude-sonnet-5`) via the Anthropic SDK |
| Embeddings / ANN | sentence-transformers + FAISS |
| Fuzzy matching | RapidFuzz |
| Tabular I/O | pandas, openpyxl |
| State | SQLite |
| Reviewer UI | React 19 + TypeScript + Vite + TanStack Query |

## Honest summary

The LLM classifies, induces a template once per family, and reads a retrieved
document. It never freely writes a value and it never writes a description.
That is why the output can be checked — and why it is cheap.
