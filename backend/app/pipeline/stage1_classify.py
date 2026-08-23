"""
Stage 1: classification (the step-back). Before extracting anything, decide
what kind of product this is and load only that category's permitted
attribute set - so extraction downstream never sees a blank 250-field form
and never invents a field outside the schema.

Stage A (router): Part_Manuf substring match. Zero model calls, covers the
majority of rows given how concentrated Part_Manuf is in this dataset
(Philips/Milwaukee/Boise Cascade/Appliance Dealers Co-op alone are >35% of
the 1,000-row sample).

Stage B (LLM): only for rows Stage A can't place. Falls back to
"Unclassified" (empty attribute schema) if the LLM is unavailable - an
unrouted row with no schema correctly produces no invented attributes.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from app.config import get_settings
from app.core.classpaths import route_by_manufacturer
from app.core.schema import ClassificationResult
from app.llm import client
from app.llm.classify import classify_row_llm


def _signature(part_manuf: str, part_desc: str) -> tuple:
    """A cache key that groups rows written in the same style by the same hand.

    Rows sharing a distributor and the same leading vocabulary are the same
    kind of product, so one classification answers for all of them. Without
    this the sample makes ~200 sequential model calls where ~20 will do.
    """
    tokens = [t.lower() for t in re.findall(r"[A-Za-z]{3,}", part_desc)]
    return (part_manuf.strip().lower(), tuple(sorted(set(tokens))[:4]))


def classify_dataframe(df: pd.DataFrame) -> list[ClassificationResult]:
    """Route what can be routed, then classify the remainder once per signature.

    Three passes so the model is called as few times as possible, and those
    calls happen concurrently rather than one row at a time:
      1. deterministic router  - zero model calls
      2. group the rest by signature, classify each unique group once
      3. map every row back to its group's answer
    """
    settings = get_settings()
    results: dict[int, ClassificationResult] = {}
    pending: dict[tuple, list[int]] = {}
    rows_by_index: dict[int, tuple[str, str]] = {}

    # ---- pass 1: deterministic router ----
    for idx, row in df.iterrows():
        routed = route_by_manufacturer(row["Part_Manuf"])
        if routed:
            results[idx] = ClassificationResult(
                row_index=idx, classpath=routed, method="router", confidence=0.9
            )
            continue
        key = _signature(row["Part_Manuf"], row["Part_Desc"])
        pending.setdefault(key, []).append(idx)
        rows_by_index[idx] = (row["Part_Desc"], row["Part_Manuf"])

    # ---- pass 2: one concurrent model call per unique signature ----
    resolved: dict[tuple, str] = {}
    if pending and client.is_configured():
        groups = list(pending.items())[: settings.max_classification_llm_calls]

        def classify_group(item):
            key, indices = item
            desc, manuf = rows_by_index[indices[0]]
            try:
                return key, classify_row_llm(indices[0], desc, manuf).classpath
            except client.LLMUnavailable:
                return key, None

        workers = max(1, min(settings.classification_concurrency, len(groups)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for key, classpath in pool.map(classify_group, groups):
                if classpath:
                    resolved[key] = classpath

    # ---- pass 3: map every unrouted row back to its group's answer ----
    for key, indices in pending.items():
        classpath = resolved.get(key)
        for idx in indices:
            if classpath:
                results[idx] = ClassificationResult(
                    row_index=idx, classpath=classpath, method="llm", confidence=0.75
                )
            else:
                # No schema means no invented attributes - the correct outcome
                # for a row nothing could place.
                results[idx] = ClassificationResult(
                    row_index=idx, classpath="Unclassified", method="fallback", confidence=0.0
                )

    return [results[idx] for idx in sorted(results)]
