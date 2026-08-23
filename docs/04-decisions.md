# 04 — Decision log

Append new decisions at the bottom. Each one records what we chose, *and what we
rejected*, so nobody re-litigates it in week two.

---

### D1 — The pipeline core is headless, file-in / file-out
**Chosen.** Evaluation hands us a CSV shaped like the sample and expects a
CSV/XLSX back. The API and the React UI are **surfaces over** the core, never
the entry point.
**Rejected:** "input the company website" pipelines, Notion/Sheets sync, live
OAuth integrations. On evaluation day they have nothing to eat, and they burn
build time on plumbing judges already own.

### D2 — Split extraction from composition
**Chosen.** The LLM produces a fact layer; descriptions are composed by pure
functions ([03](03-composition-rules.md)).
**Rejected:** prompting for all five descriptions. That is why most submissions
will ship five descriptions that quietly disagree and a 58-character
`INVOICE_DESC` that breaks the till system.

### D3 — Four provenance tiers, and no `GENERATED` tier
**Chosen.** `PARSED` / `LOOKUP` / `INFERRED` / `RETRIEVED`. A cell with no tier
is not written.
**Consequence:** we will have visibly lower fill rates than teams that
hallucinate. That is the point, and the Solution Guide explicitly rewards it —
so it must be *stated on the slide*, not left to be discovered.

### D4 — Parse templates are induced, not hardcoded
**Chosen.** Statistical slot mining per family + one LLM call to name slots.
**Proof obligation:** held-out-manufacturer accuracy must be reported. Without
that number this claim is just an assertion.

### D5 — Enrichment is gap-fill only
**Chosen.** Input values are immutable; we only ever write into empty cells.

### D6 — Two categories at full depth, not 252 columns shallow
**Chosen.** Lighting and appliances first (largest, richest ground truth), then
decking. Cut: image sourcing at scale, UPC/EAN/GTIN, country of origin,
large-scale scraping.
**Rationale:** the Solution Guide rewards a flagged gap and punishes a fabricated
value, so a deliberate, explained blank costs less than a shallow guess.

### D7 — Reviewer queue, not a spreadsheet, not Notion
**Chosen.** A React review surface reading `provenance.json`, with correction
propagation (Stage 7).
**Rejected:** Notion/Sheets sync — judges already have a PIM; it proves nothing
about extraction correctness and can fail live on stage.

### D8 — Claude is used sparingly, always inside a constraint
Three call sites only: classify (from a ~10-item shortlist), induce a template
(once per family), read a retrieved chunk (extract-or-null). Model:
`claude-sonnet-5`.

### D9 — Headers are extracted, never typed
`backend/app/core/delivery_headers.json` is generated from
`data/raw/delivery_format.csv` by `scripts/extract_headers.py`. 252 columns,
original order, byte-exact.

---

## Open questions

**Q1 — Pre-indexed spec-sheet corpus, or live retrieval during evaluation?**
Live retrieval demonstrates the sourcing rule properly but is slow and can fail
on stage. *Leaning:* pre-indexed corpus for the sample categories, with a live
fallback behind a flag. **Not yet decided.**

**Q2 — Where does `Dept`/`Class`/`Fine` come from?** Ground truth shows
`Appliances / Large Appliances / Dishwashers` alongside a separate `Classpath`.
Are these two views of one taxonomy or two independent ones? Needs a decision
before `app/core/taxonomy.py` is fleshed out.

**Q3 — `MANUFACTURER_NAME` for row 1 is `Rheem Manufacturing` with
`BRAND_NAME` `FRIGIDAIRE®`.** Frigidaire is Electrolux, not Rheem. This is
plausibly an error in the sample. Decide whether to reproduce ground truth
faithfully or resolve correctly — and say which on the slide.
