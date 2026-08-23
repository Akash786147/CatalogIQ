# 03 — Composition rules

Reverse-engineered from the two ground-truth rows in
`data/raw/delivery_format.csv`. **No LLM runs in this stage.** These are pure
functions over the validated fact layer, which is why the five descriptions
cannot contradict each other.

Reference facts (ground-truth row 1):

```
BRAND_NAME  FRIGIDAIRE®        Product Name  Dishwasher
Series      Professional Series      MPN     PDSH4816AF
With        With CleanBoost®
attrs       Wash Cycles 5 · Voltage 120 V · Amperage 15 A · Mounting Leg
            · Size 24 in W x 24-1/4 in D · Depth With Door Open 50-1/4 in
            · Sound Level 47 dBA · Material Stainless Steel
```

---

## MOBILE_DESC

```
{MANUFACTURER_NAME} {BRAND}, {Product Name}, {Series}, {MPN}[, {Mounting Type}]
```
```
Rheem Manufacturing FRIGIDAIRE, Dishwasher, Professional Series, PDSH4816AF
Whirlpool, Dishwasher, Eco Series, WDTS7024RZ, Built-in Mounting
```
Comma-joined. `®` dropped here. Short — mobile listing line.

## INVOICE_DESC — ≤ 40 chars, UPPERCASE

```
DISHWASHER LEG 5 SST 120V 15A 50-1/4IN      (38)
DISHWASHER BLTLN SST SST 120V 10A 41DBA     (39)
```

Not a template — a **constrained compression**:

1. Build a token list from the fact layer, each with a **priority weight from
   the classpath schema**: `Product Name` > mounting > headline spec > electrical
   > dimension.
2. Apply approved abbreviations: `Stainless Steel→SST`, `Built-in→BLTLN`,
   `Leg→LEG`, `inch→IN`.
3. Strip the space between number and unit here only (`120 V`→`120V`).
4. Uppercase, space-join.
5. **While `len > 40`: drop the lowest-priority token.**

Deterministic and always compliant. `test_invoice_desc_length` asserts ≤40 over
the whole corpus — if it ever fails, the build fails.

## SHORT_DESC

```
{BRAND}® {Series} {MPN} {Product Name}[ {With}], {attr values, schema order}
```
```
FRIGIDAIRE® Professional Series PDSH4816AF Dishwasher With CleanBoost®, Leg Mounting, 5-Wash Cycle, Stainless Steel
Whirlpool® Eco Series WDTS7024RZ Dishwasher, Built-in Mounting, Stainless Steel, Stainless Steel
```

Head is space-joined; the attribute tail is comma-joined. Note the **attribute
phrasing templates**: `Leg` → `Leg Mounting`, `5` → `5-Wash Cycle`. Each
attribute in the classpath schema carries a `short_form` pattern. Note also that
row 2 repeats `Stainless Steel` (Material *and* Color) — ground truth does **not**
deduplicate, so neither do we.

## LONG_DESC1

```
{BRAND}® {Product Name}[ {With}], {Series}, {every populated attr with UOM, schema order}
```
```
FRIGIDAIRE® Dishwasher With CleanBoost®, Professional Series, 5 Wash Cycles,
120 V, 15 A, Leg Mounting, 24 in W x 24-1/4 in D, 50-1/4 in Depth With Door Open,
8-1/2 in Upper Rack, 11-1/4 in Lower Rack Minimum Height, …
```

Fullest form. MPN is **not** included. Values lead, label follows
(`50-1/4 in Depth With Door Open`). Blank attributes are simply skipped — the
sentence stays grammatical because it is a comma list, not prose.

## RETAIL_DESC

```
{Series} {Product Name}, {attr values, schema order}
```
```
Professional Series Dishwasher, Leg Mounting, 5-Wash Cycle, Stainless Steel
Eco Series Dishwasher, Built-in Mounting, Stainless Steel, Stainless Steel
```

`SHORT_DESC` **minus brand and MPN**. Shopper-facing.

## MARKETING_DESCRIPTION and ITEM_FEATURES_1..20

The only prose fields — and the only ones we **do not compose**. They are
`RETRIEVED` verbatim from manufacturer documents or left blank. Row 1 has none;
row 2 has both, because Whirlpool publishes them.

Never paraphrased. Copying a manufacturer's own sentence is sourced; rewriting it
is invention wearing a nicer jacket.

---

## Formatting invariants (enforced in `app/core/units.py`)

| Rule | Example |
|---|---|
| Fractions, never decimals | `50.25 in` → `50-1/4 in` |
| Space between number and unit | `24in` → `24 in` |
| Compound dimensions keep inline units | `33-7/16 in H x 23-7/8 in W x 22-5/8 in D` |
| `®` / `™` preserved exactly | `FRIGIDAIRE®` |
| `Standard/Approvals` pipe-joined, sorted | `cUL Listed\|ENERGY STAR Certified\|UL Listed` |
| `Additional Information` comma-joined, sorted | `Folding Tines, Leak Detection System, …` |

## Asset filename generation

```
Product Image        {BRAND}_{MPN}.jpg
Alternate Image n    {BRAND}_{MPN}_{n}.jpg
Specification Sheet  {BRAND}_{MPN}_Specification_Sheet.pdf
Owners/User Manual   {BRAND}_{MPN}_Owners_User_Manual.pdf
```

Brand token is the brand with `®` stripped and spaces → `_`. These are
deterministic, so they are emitted whenever we know we hold the asset;
`Actual Image (Yes/No)` records whether the file genuinely exists rather than
being a plausible name.
