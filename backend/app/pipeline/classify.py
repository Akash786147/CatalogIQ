"""Stage 1 -- Classification. See docs/01-architecture.md.

row -> Classpath (+ Dept/Class/Fine) + the attribute schema for that classpath.

Two-stage, cheap-first:
  A. Deterministic router: Part_Manuf + keyword signature. Resolves ~70% of the
     sample with zero model calls ("Phillips Lighting (5831)" + "Led" is not
     ambiguous).
  B. LLM pick from a ~10-classpath shortlist retrieved by embedding similarity.
     Never "pick from 400".

The output is not just a label -- it is the label AND its permitted attribute
list. That object constrains every stage after this one, which is what stops the
model inventing a "wash cycle" field for a light bulb.

TODO(stage-1): implement the router table and the shortlist retriever.
"""

from __future__ import annotations

from app.core.cell import EnrichedRow


def route_deterministic(row: EnrichedRow) -> str | None:
    """Stage A. Returns a classpath, or None if the row is genuinely ambiguous."""
    raise NotImplementedError("stage-1: deterministic router")


def shortlist_classpaths(row: EnrichedRow, k: int = 10) -> list[str]:
    """Stage B, part 1. Nearest classpaths by embedding similarity."""
    raise NotImplementedError("stage-1: classpath shortlist")


def classify_batch(rows: list[EnrichedRow]) -> list[EnrichedRow]:
    """Assign classpath + attribute schema to each row.

    Until implemented, rows pass through with an empty classpath, which the
    writer renders as a blank cell -- an honest gap, not a guess.
    """
    return rows
