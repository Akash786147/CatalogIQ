"""The 252-column delivery format.

Headers are loaded from delivery_headers.json, which is generated from the
provided delivery-format CSV by scripts/extract_headers.py. They are never
hand-typed and never reordered.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_HEADERS_PATH = Path(__file__).parent / "delivery_headers.json"

# The six input columns, in their input order.
INPUT_COLUMNS: tuple[str, ...] = (
    "Mfg_Part_Num",
    "Part_Desc",
    "E1_Brand",
    "Unilog_Brand",
    "DIB_Brand",
    "Part_Manuf",
)

# Copied byte-for-byte from input to output. Never modified, never enriched.
PASSTHROUGH_COLUMNS: tuple[str, ...] = INPUT_COLUMNS

MAX_ATTRIBUTES = 50
MAX_ITEM_FEATURES = 20

# The five composed descriptions, in the order they appear in the output.
DESCRIPTION_COLUMNS: tuple[str, ...] = (
    "MOBILE_DESC",
    "INVOICE_DESC",
    "SHORT_DESC",
    "LONG_DESC1",
    "RETAIL_DESC",
)

# Hard character limits observed / specified. Asserted in tests.
CHAR_LIMITS: dict[str, int] = {
    "INVOICE_DESC": 40,
}


@lru_cache(maxsize=1)
def delivery_headers() -> list[str]:
    """All 252 output headers, in their original order."""
    with _HEADERS_PATH.open(encoding="utf-8") as f:
        headers: list[str] = json.load(f)
    if len(headers) != 252:
        raise ValueError(f"expected 252 delivery headers, found {len(headers)}")
    return headers


def attribute_columns(index: int) -> tuple[str, str, str]:
    """The (label, value, uom) header names for attribute slot `index` (1-based)."""
    if not 1 <= index <= MAX_ATTRIBUTES:
        raise ValueError(f"attribute index {index} out of range 1..{MAX_ATTRIBUTES}")
    return (
        f"ATTRIBUTE_LABEL {index}",
        f"ATTRIBUTE_VALUE {index}",
        f"ATTRIBUTE_UOM {index}",
    )


def item_feature_column(index: int) -> str:
    if not 1 <= index <= MAX_ITEM_FEATURES:
        raise ValueError(f"feature index {index} out of range 1..{MAX_ITEM_FEATURES}")
    return f"ITEM_FEATURES_{index}"
