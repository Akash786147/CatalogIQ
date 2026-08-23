"""
Stage 4: validation. Runs as a chain over each row's attribute cells; a check
can downgrade confidence or void a value to BLANK_FLAGGED, but nothing here
ever invents a new value.

- Structural: UOM normalization, decimal -> trade fraction for dimension
  attributes.
- Vocabulary: value must exist in the attribute's LOV (app.core.lov);
  near-misses below the fuzzy threshold are rejected, not snapped.
- Statistical: per-family, per-attribute outlier detection using median +
  MAD computed AT RUNTIME from that family's own PARSED/INFERRED values -
  nothing hardcoded, so it generalizes to a manufacturer never seen before.
- Plausibility: a small, explicit cross-field contradiction rule set.
"""
from __future__ import annotations

import statistics
from collections import defaultdict

from app.config import get_settings
from app.core.classpaths import ClasspathSchema
from app.core.lov import conform_to_lov
from app.core.schema import Cell, ProvenanceState
from app.core.uom import decimal_to_trade_fraction

FRACTION_ATTRIBUTES = {"Depth With Door Open", "Minimum Height", "Maximum Height", "Length", "Width"}


def validate_vocabulary(cell: Cell, schema: ClasspathSchema, label: str) -> Cell:
    attr = schema.get_attribute(label)
    if not attr or not attr.lov or cell.is_blank():
        return cell
    matched, score = conform_to_lov(str(cell.value), attr.lov)
    if matched:
        cell.value = matched
        cell.confidence = min(cell.confidence, round(score / 100, 2))
        return cell
    return Cell(state=ProvenanceState.BLANK_FLAGGED,
                reason=f"'{cell.value}' is not in the approved vocabulary for {label} (best fuzzy score {score:.0f})")


def apply_structural_formatting(cell: Cell, label: str) -> Cell:
    if cell.is_blank() or not isinstance(cell.value, (int, float)):
        return cell
    if label in FRACTION_ATTRIBUTES:
        cell.value = decimal_to_trade_fraction(float(cell.value))
    else:
        cell.value = int(cell.value) if float(cell.value).is_integer() else cell.value
    return cell


def flag_statistical_outliers(
    family_attribute_cells: dict[str, list[Cell]],
) -> None:
    """Mutates cells in place: downgrades confidence and appends a reason note
    for numeric values far outside the family's own observed distribution."""
    settings = get_settings()
    for label, cells in family_attribute_cells.items():
        numeric_cells = [c for c in cells if not c.is_blank() and isinstance(c.value, (int, float))]
        if len(numeric_cells) < 4:
            continue
        values = [float(c.value) for c in numeric_cells]
        median = statistics.median(values)
        mad = statistics.median([abs(v - median) for v in values]) or 1e-6
        for c in numeric_cells:
            z = abs(float(c.value) - median) / (1.4826 * mad)
            if z > settings.outlier_mad_threshold:
                c.confidence = round(c.confidence * 0.4, 2)
                c.reason += f" [statistical outlier vs family median {median:g}: flagged, not rejected]"


# small, explicit plausibility rules: (attribute, forbidden-if-value, requires-attribute)
CONTRADICTION_RULES = [
    {
        "trigger_label": "Standard/Approvals", "trigger_contains": "IP68",
        "requires_label": "Material", "message": "IP68 sealing claim with no material listed",
    },
]


def check_contradictions(attributes: dict[str, Cell]) -> list[str]:
    warnings = []
    for rule in CONTRADICTION_RULES:
        trig = attributes.get(rule["trigger_label"])
        if trig and not trig.is_blank() and rule["trigger_contains"].lower() in str(trig.value).lower():
            req = attributes.get(rule["requires_label"])
            if req is None or req.is_blank():
                warnings.append(rule["message"])
    return warnings
