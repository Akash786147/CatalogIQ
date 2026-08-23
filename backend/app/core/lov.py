"""
Controlled-vocabulary conformance. An attribute with an `lov` (list of values)
on its AttributeDef may ONLY take one of those values - anything else is either
fuzzy-matched onto the nearest approved value (if confident) or rejected
outright and left BLANK+FLAGGED (never silently invented or "close enough"
snapped when confidence is low).
"""
from __future__ import annotations

from rapidfuzz import fuzz, process

from app.config import get_settings

# common trade abbreviations seen in Part_Desc, expanded before fuzzy LOV matching.
# This is a general abbreviation dictionary (like UOM_CANONICAL), not a per-SKU rule -
# it doesn't pick a value, it just widens the token so genuine matches aren't rejected
# by the fuzzy-match threshold.
TRADE_ABBREVIATIONS: dict[str, str] = {
    "led": "LED",
    "cfl": "CFL",
    "flor": "Fluorescent",
    "med": "Medium (E26)",
    "cand": "Candelabra (E12)",
    "mog": "Mogul (E39)",
    "blt": "Built-in",
    "bltln": "Built-in",
}


def conform_to_lov(value: str, lov: list[str]) -> tuple[str | None, float]:
    """
    Returns (matched_value_or_None, score_0_to_100).
    Exact case-insensitive match short-circuits at 100. Known trade abbreviations
    are expanded before fuzzy matching so real matches aren't lost to the threshold.
    """
    if not value:
        return None, 0.0

    for candidate in lov:
        if value.strip().lower() == candidate.strip().lower():
            return candidate, 100.0

    expanded = TRADE_ABBREVIATIONS.get(value.strip().lower())
    if expanded:
        for candidate in lov:
            if expanded.strip().lower() == candidate.strip().lower():
                return candidate, 97.0

    settings = get_settings()
    best = process.extractOne(value, lov, scorer=fuzz.WRatio)
    if best is None:
        return None, 0.0
    match, score, _ = best
    if score >= settings.lov_fuzzy_threshold:
        return match, float(score)
    return None, float(score)
