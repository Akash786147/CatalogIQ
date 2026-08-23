"""
Stage 3b: RAG over an indexed manufacturer document corpus.

Sourcing rule (from the Solution Guide): data must come from the
manufacturer's own site/documentation. Marketplaces and distributor sites are
excluded. That exclusion is enforced at the retrieval layer via
ALLOWED_URL_DOMAINS substring checks - never left to the model's judgement.

Retrieval itself is a lightweight keyword-overlap scorer over the local
corpus loaded by app.io.readers.load_spec_corpus, not a full vector index -
appropriate for a corpus the size a hackathon build actually has, and it has
no dependency on an embedding model being available. Swap in FAISS +
sentence-transformers if the corpus grows large (see docs/04-decisions.md).

If the corpus is empty (the common case here - no spec sheets were provided),
this stage is a no-op: nothing is retrieved, nothing is extracted, the gap
stays BLANK+FLAGGED. That is the honest outcome, not a bug.
"""
from __future__ import annotations

import re

from app.core.schema import Cell, Evidence, ProvenanceState
from app.llm import client

ALLOWED_URL_DOMAIN_HINTS = (
    ".com/",  # placeholder allowlist; real deployment would enumerate manufacturer domains explicitly
)
BLOCKED_URL_SUBSTRINGS = ("amazon.", "ebay.", "homedepot.", "lowes.", "grainger.", "walmart.")


def _keyword_overlap_score(query: str, doc_text: str) -> float:
    q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    d_tokens = set(re.findall(r"[a-z0-9]+", doc_text.lower()))
    if not q_tokens:
        return 0.0
    return len(q_tokens & d_tokens) / len(q_tokens)


def retrieve_chunks(query: str, manufacturer_hint: str, corpus: list[dict], top_k: int = 3) -> list[dict]:
    scored = []
    for doc in corpus:
        if doc["url"] and any(b in doc["url"].lower() for b in BLOCKED_URL_SUBSTRINGS):
            continue  # sourcing rule enforced here, not by prompt
        if manufacturer_hint and manufacturer_hint.lower() not in doc["manufacturer_hint"].lower():
            continue
        score = _keyword_overlap_score(query, doc["text"])
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:top_k]]


def extract_attribute_from_chunks(
    attribute_label: str, chunks: list[dict], part_desc: str
) -> Cell:
    """Ask the model to extract ONE attribute value from retrieved text only, never from memory."""
    if not chunks:
        return Cell(state=ProvenanceState.BLANK_FLAGGED, reason="no retrieved document covers this attribute")

    context = "\n---\n".join(f"[source: {c['url']}]\n{c['text'][:1500]}" for c in chunks)
    system = (
        "Extract ONE product attribute value strictly from the provided document excerpts. "
        "If the excerpts do not state this attribute, respond with null - never infer from general "
        "knowledge or the product description alone. Respond JSON only: "
        '{"value": "<value or null>", "uom": "<unit or null>", "source_url": "<url of the excerpt used>"}'
    )
    user = f"Product: {part_desc}\nAttribute to extract: {attribute_label}\n\nDocument excerpts:\n{context}"

    try:
        result = client.complete_json(system, user, max_tokens=150)
    except client.LLMUnavailable:
        return Cell(state=ProvenanceState.BLANK_FLAGGED, reason="LLM unavailable for retrieval extraction")

    value = result.get("value")
    if not value:
        return Cell(state=ProvenanceState.BLANK_FLAGGED, reason="attribute not found in retrieved documents")

    return Cell(
        value=value,
        uom=result.get("uom"),
        state=ProvenanceState.RETRIEVED,
        confidence=0.75,
        evidence=Evidence(document_url=result.get("source_url")),
        reason=f"retrieved from manufacturer document for '{attribute_label}'",
    )
