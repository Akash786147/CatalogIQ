"""
Output serialization: the 252-column CSV (values only, headers untouched) and
the parallel provenance file of identical shape, where each cell holds
state + confidence + reason instead of a display value.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.core.schema import Cell, EnrichedRecord

# maps output column name -> attribute-cell key, for the fixed (non-numbered) fields
FIXED_FIELD_MAP = {
    "Mfg_Part_Num": None,       # copied straight from input, not a Cell
    "Part_Desc": None,
    "E1_Brand": None,
    "Unilog_Brand": None,
    "DIB_Brand": None,
    "Part_Manuf": None,
    "Classpath": None,
    "MANUFACTURER_NAME": "MANUFACTURER_NAME",
    "BRAND_NAME": "BRAND_NAME",
    "MOBILE_DESC": "MOBILE_DESC",
    "INVOICE_DESC": "INVOICE_DESC",
    "SHORT_DESC": "SHORT_DESC",
    "LONG_DESC1": "LONG_DESC1",
    "RETAIL_DESC": "RETAIL_DESC",
}

N_ATTRIBUTE_SLOTS = 50  # ATTRIBUTE_LABEL/VALUE/UOM 1..50, per the delivery format


def _row_to_output_dict(record: EnrichedRecord, header: list[str], raw_row: dict) -> dict:
    out = {col: "" for col in header}

    # pass through raw input columns verbatim
    out["Mfg_Part_Num"] = raw_row.get("Mfg_Part_Num", "")
    out["Part_Desc"] = raw_row.get("Part_Desc", "")
    out["E1_Brand"] = raw_row.get("E1_Brand", "")
    out["Unilog_Brand"] = raw_row.get("Unilog_Brand", "")
    out["DIB_Brand"] = raw_row.get("DIB_Brand", "")
    out["Part_Manuf"] = raw_row.get("Part_Manuf", "")
    out["Classpath"] = record.classpath

    out["MANUFACTURER_NAME"] = record.manufacturer_name.display_value()
    out["BRAND_NAME"] = record.brand_name.display_value()
    out["MOBILE_DESC"] = record.mobile_desc.display_value()
    out["INVOICE_DESC"] = record.invoice_desc.display_value()
    out["SHORT_DESC"] = record.short_desc.display_value()
    out["LONG_DESC1"] = record.long_desc1.display_value()
    out["RETAIL_DESC"] = record.retail_desc.display_value()

    # numbered attribute slots, in the order the classpath schema declares them
    for i, (label, cell) in enumerate(record.attributes.items(), start=1):
        if i > N_ATTRIBUTE_SLOTS:
            break
        out[f"ATTRIBUTE_LABEL {i}"] = label
        out[f"ATTRIBUTE_VALUE {i}"] = cell.display_value()
        out[f"ATTRIBUTE_UOM {i}"] = cell.uom or ""

    return out


def _row_to_provenance_dict(record: EnrichedRecord, header: list[str]) -> dict:
    out = {col: "" for col in header}
    out["Mfg_Part_Num"] = record.mfg_part_num
    out["Classpath"] = record.classpath

    def cell_json(cell: Cell) -> str:
        return json.dumps({
            "state": cell.state.value,
            "confidence": round(cell.confidence, 3),
            "reason": cell.reason,
            "evidence": cell.evidence.model_dump(exclude_none=True),
        }, ensure_ascii=False)

    for field, cell in [
        ("MANUFACTURER_NAME", record.manufacturer_name),
        ("BRAND_NAME", record.brand_name),
        ("MOBILE_DESC", record.mobile_desc),
        ("INVOICE_DESC", record.invoice_desc),
        ("SHORT_DESC", record.short_desc),
        ("LONG_DESC1", record.long_desc1),
        ("RETAIL_DESC", record.retail_desc),
    ]:
        if field in out:
            out[field] = cell_json(cell)

    for i, (label, cell) in enumerate(record.attributes.items(), start=1):
        if i > N_ATTRIBUTE_SLOTS:
            break
        out[f"ATTRIBUTE_VALUE {i}"] = cell_json(cell)

    return out


def write_output(
    records: list[EnrichedRecord],
    raw_rows: list[dict],
    header: list[str],
    output_path: Path,
) -> None:
    rows = [_row_to_output_dict(r, header, raw) for r, raw in zip(records, raw_rows)]
    df = pd.DataFrame(rows, columns=header)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".xlsx":
        df.to_excel(output_path, index=False)
    else:
        df.to_csv(output_path, index=False)


def write_provenance(records: list[EnrichedRecord], header: list[str], output_path: Path) -> None:
    rows = [_row_to_provenance_dict(r, header) for r in records]
    df = pd.DataFrame(rows, columns=header)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
