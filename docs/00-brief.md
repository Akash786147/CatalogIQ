# 00 — The brief, and what the data actually is

## What Unilog does

Unilog builds product content for industrial distributors — the manufacturer
names, titles, descriptions, attributes and images that let a buyer find and
trust a product. Their customers hand them catalogues of near-useless part rows
and expect a loadable, searchable, trustworthy catalogue back.

## Three business problems the output must solve

1. **The buyer can't find it.** `573352 40W Led Med 27k 2pk` does not match the
   search `2700K medium base LED`.
2. **The buyer doesn't trust it.** No specs, no consistent title, no source.
3. **Fixing it by hand is too slow.** ~15 SKUs/analyst/day.

## What evaluation day actually looks like

> "capable of processing the evaluation test dataset during assessment" …
> "generate a downloadable XLSX or CSV from the given input data, with all the
> required static headers populated."

Someone hands the system a CSV shaped **exactly like the sample**: six columns
of abbreviated text. No company website, no catalogue PDF, no technical docs
supplied.

**This is the single most important constraint.** Any design whose entry point
is "give me the company website" or "connect your Notion" has nothing to eat on
evaluation day and scores zero — not because it is bad, but because it answers a
question nobody asked. **The pipeline core must be file-in, file-out and
headless.** Everything else is a surface on top of it.

## What the input really contains

Profiled from `backend/data/raw/input_sample.csv` (1,000 rows, 76 distinct
`Part_Manuf`):

### Brand columns are almost entirely empty

| Column | Placeholder | Count |
|---|---|---|
| `Unilog_Brand` | `-- No Unilog Brand --` | **1000 / 1000** |
| `E1_Brand` | `-- Unbranded --` | **799 / 1000** |
| `DIB_Brand` | `-- No DIB Brand --` | 755 / 1000 |

So for ~80% of rows there is **no brand signal at all**. Brand must be recovered
from the description string and the `Part_Manuf` code.

### `Part_Manuf` is a *distributor*, not a manufacturer

Ground truth row 1:

```
Part_Manuf          = "Appliance Dealers Cooperative (APPDE)"
MANUFACTURER_NAME   = "Rheem Manufacturing"
BRAND_NAME          = "FRIGIDAIRE®"
```

A naive system copies `Part_Manuf` into `MANUFACTURER_NAME` and fails every row.
Manufacturer, brand, and distributor are three different things and the input
gives you the wrong one.

The distributor strings are themselves dirty — `Phillips Lighting (5831)`
(two L's) for what is really **Philips**; `Black & Decker/dewlt (2585)` for
**DeWalt**. Entity resolution is a real part of the job, not a formality.

### The category mix is not what the Solution Guide implies

The guide directs everyone to go deep on Faucets/Fittings. Those barely exist in
the sample. What is actually there:

| Domain | Rows | Sources |
|---|---|---|
| Lighting | ~208 | Philips 111, Kichler 56, Satco 41 |
| Power-tool accessories | ~209 | Milwaukee 108, DeWalt 55, Freud/Diablo 46 |
| Composite decking | ~140 | Boise Cascade 85, Parksite 55 (TREX/AZEK/TimberTech) |
| Appliances | 84 | Appliance Dealers Cooperative |

`E1_Brand` carries TREX (122) and TIMBERTECH (55) — decking is the one place the
brand column is actually populated.

**Depth on lighting + decking + appliances is depth on the data the evaluators
will actually test.** Two categories done to full depth beats 252 columns done
shallowly everywhere.

## What "good" looks like, per the Solution Guide

- Data must come from **the manufacturer's own site or documentation**.
  Marketplaces (Amazon, Grainger, eBay…) are explicitly excluded.
- A fluent description assembled from invented values **scores zero**.
- Flagging a gap is **rewarded**. Inventing a value to fill it is punished.

That last pair is the whole thesis. See
[01-architecture.md](01-architecture.md).

## Deliberately out of scope

Cut, and said out loud on the slide with a reason:

- Image sourcing at scale (filenames are still generated — see
  [03-composition-rules.md](03-composition-rules.md))
- UPC / EAN / GTIN
- Country of origin
- Web scraping at scale

Time freed goes to two categories at full depth and to the reviewer queue.
