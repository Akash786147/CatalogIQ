"""Input readers.

Two jobs beyond plain CSV parsing:
  1. Repair the cp1252 mangling in the provided files -- (R) reads as U+FFFD.
  2. Normalise placeholder tokens to None, so no stage mistakes
     "-- Unbranded --" for a brand.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

from app.core.constants import is_null
from app.core.schema import INPUT_COLUMNS

# The provided CSVs were written as cp1252 and re-encoded badly, so the
# registered-trademark sign arrives as the replacement character. Ground truth
# preserves (R) exactly, so we have to put it back.
_MOJIBAKE_REPAIRS = {
    "�": "®",  # -> (R)
    "â": "’",  # -> right single quote
    "â": "“",
    "â": "”",
}


def repair_encoding(text: str) -> str:
    """Undo the cp1252 damage in the provided files. See docs/02-data-contract.md."""
    for bad, good in _MOJIBAKE_REPAIRS.items():
        text = text.replace(bad, good)
    return text


def read_input_rows(path: Path) -> Iterator[dict[str, str | None]]:
    """Yield input rows with placeholders normalised to None.

    Raises if the file does not carry the six expected input columns -- better a
    loud failure now than a silently empty enrichment run.
    """
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = set(INPUT_COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name} is missing input columns: {sorted(missing)}")

        for raw in reader:
            yield {
                col: None if is_null(raw.get(col)) else repair_encoding((raw[col] or "").strip())
                for col in INPUT_COLUMNS
            }


def read_ground_truth(path: Path) -> list[dict[str, str]]:
    """The labelled delivery-format rows, encoding repaired.

    Currently 2 rows. Enough to pin the composition formulas, not enough for an
    accuracy number -- see docs/05-evaluation.md.
    """
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{k: repair_encoding(v or "") for k, v in row.items()} for row in csv.DictReader(f)]
