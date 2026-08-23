# 05 — Evaluation

Field-level accuracy is table stakes; everyone will show it. These are the
metrics that signal we know what we're doing.

Run: `python -m app.cli evaluate --pred ../backend/data/output/enriched.csv --truth ../backend/data/raw/delivery_format.csv`

| # | Metric | Why it matters |
|---|---|---|
| 1 | **Field-level accuracy**, per field and per category | The baseline. Broken out, because an average hides that descriptions are easy and attributes are hard. |
| 2 | **Coverage–accuracy curve** — accuracy at 100% / 90% / 70% auto-approval | Answers the real business question: *how much can we ship unreviewed?* |
| 3 | **Calibration plot** | Does 0.9 confidence actually mean 90% correct? Isotonic regression on the labelled rows. **The chart that most signals competence** — almost nobody does it. |
| 4 | **LOV conformance %** | Share of values inside the controlled vocabulary. Proves we constrained the model rather than trusting it. |
| 5 | **Character-limit compliance** | Asserted in tests, so it is 100% or the build fails. `INVOICE_DESC ≤ 40`. |
| 6 | **Held-out-manufacturer accuracy** | Hold out a manufacturer entirely, induce templates fresh. **The no-hardcoding proof** — this is the number that backs D4. |
| 7 | **Cost + latency per 1,000 SKUs** | Model calls amortise per family, not per row. Should be strikingly low. |
| 8 | **Analyst-hours saved** | `(rows_auto_approved / 15 SKUs per day) × 8h`. The number a judge repeats afterwards. |

## The honest metric

Report **fill rate alongside accuracy**, never accuracy alone. A system that
fills 60% of cells at 97% accuracy is more valuable than one that fills 100% at
70% — because the second one costs a human a full re-check of everything, which
is the problem we claimed to solve. Say this out loud; it reframes a weakness as
the thesis.

## The demo

1. Search `2700K medium base LED` against raw `Part_Desc` → **nothing**.
2. Same search against enriched output → **the correct Philips SKUs**.
3. Open the flagged queue: `Black & Decker/dewlt (2585)` mapped to the wrong
   manufacturer. Fix it once.
4. System reports: **"applied to 55 rows, 3 now need re-review."**
5. Counter: **analyst-hours saved: 41.**

Steps 3–4 are the moment. Everything else is setup.

## Ground truth caveat

`backend/data/raw/delivery_format.csv` contains **2 labelled rows**. That is enough to
pin the composition formulas ([03](03-composition-rules.md)) and the formatting
invariants, and **not** enough to compute a meaningful accuracy number.

Before any accuracy figure goes on a slide we need a hand-labelled set — target
**50 rows across lighting, appliances and decking**. Until that exists, metrics
1–3 and 6 are unavailable and quoting them would be fabrication. Metrics 4, 5
and 7 are computable today, since they measure our own output, not agreement
with truth.
