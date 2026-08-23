# CatalogIQ

**Evidence-first product content enrichment for industrial distributors.**

Takes a CSV of 6 columns of abbreviated distributor junk and produces the full
252-column Unilog delivery format — where **every populated cell carries
provenance and a confidence score**, and anything unsupported is left blank and
flagged rather than invented.

Built for UniHack (Unilog challenge).

---

## The one-paragraph pitch

The bottleneck at a company like Unilog isn't *generating* product content —
it's *reviewing* it. A human content analyst enriches ~15 SKUs a day. An AI that
emits 10,000 rows of unverifiable text creates more work, not less, because
someone still has to check all of it. So CatalogIQ isn't "AI fills the sheet."
It's **"AI fills the sheet and tells you exactly which 8% of cells to look at."**

## The four decisions that carry the project

1. **Extraction is split from composition.** The LLM's only job is to produce a
   validated *attribute layer*. All five descriptions (`MOBILE_DESC`,
   `INVOICE_DESC`, `SHORT_DESC`, `LONG_DESC1`, `RETAIL_DESC`) are then composed
   *deterministically* from that one layer. Mutual consistency becomes
   structural, not prompted-for. `INVOICE_DESC ≤ 40 chars` becomes a compression
   algorithm with a test assertion, not a hope.

2. **Every cell carries provenance.** Four tiers — `PARSED` (from the input
   string, with the character span), `LOOKUP` (matched a controlled vocabulary),
   `INFERRED` (cross-row consensus, with contributing SKUs), `RETRIEVED`
   (manufacturer document, with URL). A value with none of these is not written.

3. **The abbreviation grammar is learned from the corpus, not hardcoded.**
   `573352 40W Led Med 27k 2pk` is parsed by a template *induced* from the 111
   sibling Philips rows, not from a dictionary we typed. Provable by holding out
   an entire manufacturer.

4. **Cross-row consensus.** Rows are not independent. 108 Milwaukee accessories
   share a naming grammar; 122 TREX rows share a decking attribute skeleton.
   Sparse rows inherit attributes verified across their siblings, with the
   inheritance recorded as provenance.

## Repo layout

```
docs/              Start here. The design, the data contract, the decisions.
backend/           Python: FastAPI + the enrichment pipeline.
backend/data/raw/  The provided sample input + delivery format (ground truth).
frontend/          React + Vite: the reviewer queue.
scripts/           One-off analysis and evaluation runners.
```

## Docs — read in this order

| Doc | What it answers |
|---|---|
| [docs/00-brief.md](docs/00-brief.md) | What the challenge actually asks for, and what the data really looks like |
| [docs/01-architecture.md](docs/01-architecture.md) | The 7-stage pipeline and the module map |
| [docs/02-data-contract.md](docs/02-data-contract.md) | Input columns, the 252 output columns, the provenance cell schema |
| [docs/03-composition-rules.md](docs/03-composition-rules.md) | Description formulas reverse-engineered from ground truth |
| [docs/04-decisions.md](docs/04-decisions.md) | Decision log — what we chose and what we deliberately cut |
| [docs/05-evaluation.md](docs/05-evaluation.md) | The metrics we put on the slide, and how each is computed |

## Quickstart

**Backend**
```bash
cd backend
python -m venv .venv && .venv/Scripts/activate     # Windows
pip install -e ".[dev]"
cp .env.example .env                                # add GROQ_API_KEY / OPENROUTER_API_KEY
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev                                          # http://localhost:5173
```

The frontend proxies `/api` to `http://localhost:8000` (see
`frontend/vite.config.ts`), so no CORS config is needed in development.

**Headless (this is what gets evaluated)**
```bash
cd backend
python -m app.cli enrich --input data/raw/input_sample.csv \
                         --output data/output/enriched.csv
```

## Status

Scaffolded. See [docs/05-evaluation.md](docs/05-evaluation.md) for what is
measured and [docs/04-decisions.md](docs/04-decisions.md) for open questions.
