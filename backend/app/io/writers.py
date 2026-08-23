"""Output writers.

Two files of identical shape:
  enriched.csv    -- the 252 columns, values only, headers untouched
  provenance.json -- the same cells as full objects, for the reviewer UI
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from app.core.cell import EnrichedRow
from app.core.schema import (
    MAX_ATTRIBUTES,
    attribute_columns,
    delivery_headers,
)


def _flatten(row: EnrichedRow) -> dict[str, str]:
    """Collapse an EnrichedRow into the flat 252-column view.

    Unsourced cells become blank strings -- Cell.as_output() enforces that.
    """
    out: dict[str, str] = {h: "" for h in delivery_headers()}

    # Input passthrough: byte-for-byte, never enriched.
    for col, value in row.source.items():
        if col in out:
            out[col] = value or ""

    out["Classpath"] = row.classpath.as_output()

    for header, cell in row.fields.items():
        if header in out:
            out[header] = cell.as_output()

    # Attribute triplets. The label is emitted even when the value is unknown --
    # the label set is the checklist, the blanks are the honest gaps.
    for i, attr in enumerate(row.attributes[:MAX_ATTRIBUTES], start=1):
        label_col, value_col, uom_col = attribute_columns(i)
        out[label_col] = attr.label
        out[value_col] = attr.cell.as_output()
        out[uom_col] = attr.uom if attr.cell.is_populated else ""

    return out


def write_csv(rows: list[EnrichedRow], path: Path) -> Path:
    """Write the deliverable. All 252 headers, original order, always."""
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = delivery_headers()
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(_flatten(row))
    return path


def write_xlsx(rows: list[EnrichedRow], path: Path) -> Path:
    """Same content as write_csv, as a workbook. The brief accepts either."""
    import pandas as pd

    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame([_flatten(r) for r in rows], columns=delivery_headers())
    frame.to_excel(path, index=False, engine="openpyxl")
    return path


def write_provenance(rows: list[EnrichedRow], path: Path) -> Path:
    """The parallel evidence file the reviewer queue reads."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [row.model_dump(mode="json") for row in rows]
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path
