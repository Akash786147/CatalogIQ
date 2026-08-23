# 02 — Data contract

## Input (6 columns, exactly)

| Column | Reality |
|---|---|
| `Mfg_Part_Num` | Manufacturer part number. Usually reliable. Sometimes prefixed (`3MABR-7100075678`). |
| `Part_Desc` | The abbreviated junk. **This is the primary evidence source.** Often begins with the MPN. |
| `E1_Brand` | `-- Unbranded --` in 799/1000 |
| `Unilog_Brand` | `-- No Unilog Brand --` in **1000/1000** — carries zero signal |
| `DIB_Brand` | `-- No DIB Brand --` in 755/1000 |
| `Part_Manuf` | **A distributor**, not a manufacturer. 76 distinct values, dirty spelling. |

Placeholder tokens that must be treated as **null, not as a value**:

```
-- Unbranded --      -- No Unilog Brand --      -- No DIB Brand --      -
```

`app/core/constants.py :: NULL_TOKENS`

## Output (252 columns)

Headers are checked in verbatim at
`backend/app/core/delivery_headers.json`, extracted programmatically from
`data/raw/delivery_format.csv`. **They are never hand-typed and never
reordered.** The writer emits all 252 in the original order, populated or blank.

### Column groups

| Range | Group | Notes |
|---|---|---|
| 0–5 | Source URLs | `MFR URL`, `Ref URL 1..5` — manufacturer domains only |
| 6–10 | Identifiers | `PART_NUMBER`, `Dept`, `Class`, `Fine`, `SKU - MY_PART_NUMBER` |
| 11–16 | **Input passthrough** | Copied byte-for-byte from the input. Never modified. |
| 17–22 | Entity resolution | `MANUFACTURER_NAME`, `BRAND_NAME`, `TRADE_NAME`, `MANUFACTURER_PART_NUMBER`, `ALTERNATE_PART_NUMBER`, `Classpath` |
| 23–28 | **The five descriptions** + `MARKETING_DESCRIPTION` | Composed, never generated |
| 29–48 | `ITEM_FEATURES_1..20` | Bullet features, from manufacturer docs only |
| 49–54 | Qualifiers | `With`, `Standard/Approvals`, `Prop 65`, `Application`, `Includes`, `Product Name` |
| 55–204 | **`ATTRIBUTE_LABEL/VALUE/UOM 1..50`** | The fact layer. See below. |
| 205–213 | Commerce | `UPC`, `EAN`, `GTIN`, `UNSPSC`, `Warranty`, pricing, packaging |
| 214–223 | Dimensions | `LENGTH/HEIGHT/WIDTH/WEIGHT/VOLUME` each with a `_UOM` |
| 224–228 | Images | `Product Image`, `Alternate Image 1..4` |
| 229–248 | Documents | SDS, manuals, spec sheet, drawings, videos |
| 249–251 | Flags | `Country Of Origin`, `Discontinued`, `Actual Image (Yes/No)` |

### The attribute triplets are the heart of it

`ATTRIBUTE_LABEL n` / `ATTRIBUTE_VALUE n` / `ATTRIBUTE_UOM n`, n = 1..50.

Ground truth, both dishwasher rows, emits **the same 15 labels in the same
order** — because the label set belongs to the *classpath*, not to the row:

```
1  Series                 9   Depth With Door Open
2  Model                  10  Minimum Height
3  Number of Wash Cycles  11  Maximum Height
4  Voltage Rating         12  Sound Level
5  Amperage Rating        13  Material
6  Mounting Type          14  Color
7  Plug Type              15  Additional Information
8  Size
```

Row 1 leaves `Model`, `Plug Type` and `Color` blank. Row 2 additionally leaves
`Number of Wash Cycles` and `Maximum Height` blank.

**This is the ground truth doing exactly what we claim to do: emit the checklist,
fill what is evidenced, leave the rest blank.** The label ordering is a
per-classpath schema object in `app/core/schemas/`; the values are whatever
survived validation.

Value/UOM split, as observed:
- Scalar with a unit → value `47`, uom `dBA`
- Compound dimension → value `24 in W x 24-1/4 in D`, uom **blank** (the units
  are inline)
- Enumerated → value `Stainless Steel`, uom blank
- Multi-fact rollup → `Additional Information` takes a comma-joined,
  alphabetically sorted list

### Conventions read off the ground truth

- **Fractions, not decimals.** `50-1/4 in`, `23-7/8 in`, `33-7/16 in`. Never
  `50.25`.
- **Space between number and unit.** `120 V`, `15 A`, `47 dBA`.
- **`®` is preserved** on `BRAND_NAME` and inside descriptions (`FRIGIDAIRE®`,
  `Whirlpool®`). ⚠️ The provided CSV is **cp1252-mangled** — `®` reads as
  `U+FFFD`. Readers must repair this; see `app/io/readers.py`.
- **`Standard/Approvals` is pipe-delimited and alphabetically sorted:**
  `ASSE 1006|CEE Tier 2 Qualified|cUL Listed|ENERGY STAR Certified|NSF Certified|UL Listed`
- **Asset filenames are deterministic**, not URLs:
  `FRIGIDAIRE_PDSH4816AF.jpg`, `FRIGIDAIRE_PDSH4816AF_1.jpg`,
  `Whirlpool_WDTS7024RZ_Specification_Sheet.pdf`
  → `{BRAND}_{MPN}[_{n}].jpg` and `{BRAND}_{MPN}_{Doc_Type}.pdf`. Generatable
  without sourcing the asset; `Actual Image (Yes/No)` records whether we truly
  have it.

## The internal representation

Never a bare string. Every value is a `Cell`:

```python
class Provenance(str, Enum):
    PARSED    = "PARSED"      # from the input string, with a character span
    LOOKUP    = "LOOKUP"      # matched a controlled vocabulary
    INFERRED  = "INFERRED"    # cross-row consensus, with contributing SKUs
    RETRIEVED = "RETRIEVED"   # manufacturer document, with a URL
    # there is deliberately no GENERATED tier

class Cell(BaseModel):
    value: str | None
    uom: str | None = None
    state: Provenance | None = None      # None ⇒ an honest gap
    confidence: float = 0.0
    evidence: Evidence | None = None
    reason: str | None = None
```

**A cell with no `state` is never written.** That single invariant is what makes
the system architecturally incapable of the failure mode the Solution Guide says
scores zero.

## Two files out, same shape

| File | Content |
|---|---|
| `enriched.csv` / `.xlsx` | The 252 columns, values only, headers untouched |
| `provenance.json` | Identical shape, each cell the full object above |

The reviewer UI reads the second. The evaluator reads the first.
