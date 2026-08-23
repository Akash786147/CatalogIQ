"""
Unit-of-measure normalization and decimal->trade-fraction conversion.

Deterministic, table-driven - no model calls. This is Stage 4's "structural"
validation pass: units drawn from the approved UOM list, decimals converted to
the mixed-fraction notation tradespeople actually search in
(0.5 -> 1/2, 50.25 in -> 50-1/4 in).
"""
from __future__ import annotations

import re
from fractions import Fraction

# canonical UOM table: raw token (lowercased, punctuation stripped) -> canonical symbol
UOM_CANONICAL: dict[str, str] = {
    "w": "W", "watt": "W", "watts": "W",
    "v": "V", "volt": "V", "volts": "V",
    "a": "A", "amp": "A", "amps": "A", "ampere": "A",
    "k": "K", "kelvin": "K",
    "in": "in", "inch": "in", "inches": "in", '"': "in",
    "ft": "ft", "foot": "ft", "feet": "ft", "'": "ft",
    "lm": "lm", "lumen": "lm", "lumens": "lm",
    "dba": "dBA", "db": "dBA",
    "pk": "ea", "pc": "ea", "pcs": "ea",
    "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "g": "g", "gram": "g", "grams": "g",
}

# fraction denominator we snap to when converting trade dimensions (1/64" precision,
# same convention used throughout the ground-truth delivery format: "50-1/4 in")
_TRADE_DENOMINATOR = 64


def canonical_uom(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip().lower().rstrip(".")
    return UOM_CANONICAL.get(key, raw.strip() or None)


def decimal_to_trade_fraction(value: float) -> str:
    """
    50.25 -> '50-1/4'
    0.5   -> '1/2'
    12.0  -> '12'
    Snaps to the nearest 1/64 the way a distributor catalogue does.
    """
    whole = int(value)
    frac_part = abs(value - whole)
    frac = Fraction(frac_part).limit_denominator(_TRADE_DENOMINATOR)

    if frac == 0:
        return str(whole)
    if whole == 0:
        return f"{frac.numerator}/{frac.denominator}"
    return f"{whole}-{frac.numerator}/{frac.denominator}"


_DIM_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(in|ft|w|v|a|k|lm|dba|db|pk|pc|pcs|lb|lbs|g)\s*$", re.IGNORECASE)


def normalize_dimension(text: str) -> tuple[float, str] | None:
    """Parse a raw '24in' / '0.5 in' style token into (numeric_value, canonical_uom)."""
    m = _DIM_RE.match(text)
    if not m:
        return None
    value = float(m.group(1))
    uom = canonical_uom(m.group(2))
    return value, uom


def format_measurement(value: float, uom: str | None, as_fraction: bool = False) -> str:
    if as_fraction:
        num = decimal_to_trade_fraction(value)
    else:
        num = str(int(value)) if float(value).is_integer() else str(value)
    return f"{num} {uom}" if uom else num
