"""
Stage 5: deterministic composition. The LLM's job stops at producing a
validated fact layer (Stage 2-4's output). All five description fields are
assembled from that single fact layer by fixed formulas - never written by
a model - so they cannot contradict each other and INVOICE_DESC's 40-char
limit is a compression algorithm, not a hope.

Field-order and priority come from each classpath's AttributeDef list
(app.core.classpaths), so this is data-driven rather than per-category code.
The formula shapes below were reverse-engineered from the one ground-truth
example available (a Dishwasher row in delivery_format.csv) and generalized
across classpaths using the same priority-ordered structure - see
docs/03-composition-rules.md for the exact reverse-engineering and the
documented limitation that only one category has a real ground-truth example
to validate against.
"""
from __future__ import annotations

from app.core.classpaths import ClasspathSchema
from app.core.schema import Cell, ProvenanceState
from app.core.uom import UOM_CANONICAL

INVOICE_MAX_CHARS = 40

# compact abbreviations used only in the 40-char INVOICE_DESC line
INVOICE_VALUE_ABBREV = {
    "stainless steel": "SST", "built-in": "BLTIN", "leg": "LEG",
}


def _fmt_attr(label: str, cell: Cell) -> str:
    if cell.is_blank():
        return ""
    uom = f" {cell.uom}" if cell.uom else ""
    return f"{cell.value}{uom}"


def _ordered_nonblank(attributes: dict[str, Cell], schema: ClasspathSchema, max_priority: int | None = None):
    order = {a.label: a.priority for a in schema.attributes}
    items = [(label, cell) for label, cell in attributes.items() if not cell.is_blank()]
    items.sort(key=lambda kv: order.get(kv[0], 99))
    if max_priority is not None:
        items = [(l, c) for l, c in items if order.get(l, 99) <= max_priority]
    return items


def compose_mobile_desc(
    manufacturer: Cell, brand: Cell, item_type: str, mpn: str,
    attributes: dict[str, Cell], schema: ClasspathSchema,
) -> Cell:
    mfr_val, brand_val = manufacturer.display_value(), brand.display_value()
    parts = [p for p in [mfr_val, brand_val if brand_val != mfr_val else ""] if p]
    head = " ".join(parts)
    top = _ordered_nonblank(attributes, schema, max_priority=2)
    series_like = next((_fmt_attr(l, c) for l, c in top if l in ("Series",)), None)

    pieces = [head, item_type]
    if series_like:
        pieces.append(series_like)
    if mpn:
        pieces.append(mpn)
    value = ", ".join(p for p in pieces if p)
    return Cell(value=value, state=ProvenanceState.LOOKUP, confidence=0.85,
                reason="composed deterministically from manufacturer, brand, item type, series, MPN")


def compose_short_desc(
    brand: Cell, item_type: str, mpn: str, attributes: dict[str, Cell], schema: ClasspathSchema,
) -> Cell:
    top = _ordered_nonblank(attributes, schema, max_priority=3)
    lead = " ".join(p for p in [brand.display_value(), mpn] if p)
    attr_phrase = ", ".join(_fmt_attr(l, c) for l, c in top if l != "Series")
    series = next((_fmt_attr(l, c) for l, c in top if l == "Series"), None)
    pieces = [p for p in [lead, series, item_type] if p]
    value = " ".join(pieces)
    if attr_phrase:
        value += f", {attr_phrase}"
    return Cell(value=value, state=ProvenanceState.LOOKUP, confidence=0.8,
                reason="composed from brand, top-priority attributes, item type")


def compose_long_desc1(
    brand: Cell, item_type: str, attributes: dict[str, Cell], schema: ClasspathSchema,
) -> Cell:
    ordered = _ordered_nonblank(attributes, schema)
    normal = [(l, c) for l, c in ordered if l != "Additional Information"]
    extra = next((c for l, c in ordered if l == "Additional Information"), None)

    lead = f"{brand.display_value()} {item_type}".strip()
    # readable form: bare "value uom" for a few self-explanatory fields (Sound Level,
    # Voltage/Amperage Rating), "label value uom" for everything else - matches the
    # ground-truth dishwasher example's style.
    body_parts = []
    for l, c in normal:
        if l == "Series":
            continue
        val = _fmt_attr(l, c)
        body_parts.append(f"{val}" if l in ("Sound Level", "Voltage Rating", "Amperage Rating") else f"{l} {val}" if l not in ("Material", "Color") else val)
    value = f"{lead}, " + ", ".join(body_parts)
    if extra and not extra.is_blank():
        value += f". Additional Information: {extra.value}"
    return Cell(value=value, state=ProvenanceState.LOOKUP, confidence=0.75,
                reason="composed long-form description from full validated attribute set")


def compose_retail_desc(
    item_type: str, attributes: dict[str, Cell], schema: ClasspathSchema,
) -> Cell:
    top = _ordered_nonblank(attributes, schema, max_priority=3)
    series = next((_fmt_attr(l, c) for l, c in top if l == "Series"), None)
    rest = ", ".join(_fmt_attr(l, c) for l, c in top if l != "Series")
    pieces = [p for p in [series, item_type] if p]
    value = " ".join(pieces)
    if rest:
        value += f", {rest}"
    return Cell(value=value, state=ProvenanceState.LOOKUP, confidence=0.75,
                reason="composed retail-facing description from top-priority attributes")


def compose_invoice_desc(
    item_type: str, attributes: dict[str, Cell], schema: ClasspathSchema,
) -> Cell:
    """Deterministic compression: greedy token-dropping by priority until <=40 chars."""
    tokens = [item_type.upper()]
    ordered = _ordered_nonblank(attributes, schema)
    for label, cell in ordered:
        val = str(cell.value)
        val = INVOICE_VALUE_ABBREV.get(val.lower(), val)
        uom = (cell.uom or "").upper()
        token = f"{val}{uom}" if uom and uom in UOM_CANONICAL.values() else val
        tokens.append(token.upper())

    def render(toks: list[str]) -> str:
        return " ".join(toks)

    # drop lowest-priority (last) tokens until it fits
    order = {a.label: a.priority for a in schema.attributes}
    priority_order = sorted(range(1, len(tokens)), key=lambda i: -order.get(ordered[i - 1][0], 99))
    keep = set(range(len(tokens)))
    while len(render([tokens[i] for i in sorted(keep)])) > INVOICE_MAX_CHARS and priority_order:
        drop = priority_order.pop(0)
        keep.discard(drop)

    value = render([tokens[i] for i in sorted(keep)])
    if len(value) > INVOICE_MAX_CHARS:
        value = value[:INVOICE_MAX_CHARS].rstrip()

    return Cell(value=value, state=ProvenanceState.LOOKUP, confidence=0.9,
                reason=f"greedy-compressed to <={INVOICE_MAX_CHARS} chars by attribute priority")
