"""
Stage 3: enrichment, gap-fill only, in strict source order. Never overwrites
a value already produced by Stage 2 parsing.

3a. Cross-row consensus - sparse rows inherit attributes verified across
    siblings in the same (Part_Manuf, classpath) family, when enough siblings
    agree. Pure computation, no model call.
3b. Manufacturer document RAG (app.llm.retrieval_extract) - only fires if a
    local spec corpus is present; otherwise a documented no-op.
3c. Nothing. The gap stays BLANK_FLAGGED.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from app.config import get_settings
from app.core.schema import Cell, Evidence, ProvenanceState
from app.io.readers import load_spec_corpus
from app.llm import client
from app.llm.retrieval_extract import extract_attribute_from_chunks, retrieve_chunks


def cross_row_consensus(
    family_records: list[tuple[str, dict[str, Cell]]],
) -> dict[str, dict[str, Cell]]:
    """
    family_records: [(mfg_part_num, {attribute_label: Cell}), ...] for one family.
    Returns {mfg_part_num: {attribute_label: consensus_Cell}} - ONLY for rows/labels
    that were missing and got filled; callers merge this into existing attributes
    without overwriting anything already present.
    """
    settings = get_settings()

    # value -> list of contributing MPNs, per attribute label
    votes: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for mpn, attrs in family_records:
        for label, cell in attrs.items():
            if not cell.is_blank():
                votes[label][str(cell.value)].append(mpn)

    consensus_value: dict[str, tuple[str, list[str]]] = {}
    for label, value_votes in votes.items():
        total = sum(len(mpns) for mpns in value_votes.values())
        best_value, best_mpns = max(value_votes.items(), key=lambda kv: len(kv[1]))
        agreement_ratio = len(best_mpns) / total if total else 0.0
        if len(best_mpns) >= settings.min_consensus_siblings and agreement_ratio >= settings.consensus_agreement_ratio:
            consensus_value[label] = (best_value, best_mpns)

    fills: dict[str, dict[str, Cell]] = defaultdict(dict)
    for mpn, attrs in family_records:
        for label, (value, contributing_mpns) in consensus_value.items():
            if label in attrs and not attrs[label].is_blank():
                continue  # never overwrite an existing value
            if mpn in contributing_mpns:
                continue  # don't "infer" a row's own contributed value back onto itself
            fills[mpn][label] = Cell(
                value=value,
                state=ProvenanceState.INFERRED,
                confidence=round(min(0.85, 0.5 + 0.05 * len(contributing_mpns)), 2),
                evidence=Evidence(sibling_skus=contributing_mpns[:10]),
                reason=f"inferred from {len(contributing_mpns)} sibling rows agreeing on this value",
            )
    return fills


def retrieval_enrich(
    part_desc: str, manufacturer_hint: str, missing_labels: list[str]
) -> dict[str, Cell]:
    """3b - only produces cells for labels the corpus can actually support."""
    settings = get_settings()
    corpus = load_spec_corpus(settings.spec_corpus_dir)
    if not corpus or not client.is_configured():
        return {}

    filled: dict[str, Cell] = {}
    for label in missing_labels:
        query = f"{part_desc} {label}"
        chunks = retrieve_chunks(query, manufacturer_hint, corpus)
        if not chunks:
            continue
        cell = extract_attribute_from_chunks(label, chunks, part_desc)
        if not cell.is_blank():
            filled[label] = cell
    return filled
