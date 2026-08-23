"""Stage 2, passes 2-3 -- mine and name the slots. See docs/01-architecture.md.

ONE LLM call per (manufacturer x classpath) family, not per row. Input: ~20
sample descriptions + the mined slot structure + the classpath attribute schema.
Output: a reusable parse template

    slot_2: <int>W   -> Wattage             (UOM: W)
    slot_4: <int>k   -> Color Temperature   (UOM: K, x100)
    slot_5: <int>pk  -> Package Quantity

which then runs deterministically across all rows in the family. This
amortisation is what makes cost per 1,000 SKUs low enough to put on a slide.

Nothing here may be hardcoded -- the generalisation proof is holding out an
entire manufacturer and re-inducing from scratch (docs/04-decisions.md D4).

TODO(stage-2): implement slot mining and the single naming call.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Slot:
    """One positional slot mined from a family of descriptions."""

    index: int
    shape: str  # e.g. "<int>W", "<word>", "<alnum>"
    is_variable: bool  # varies across the family => a field, not boilerplate
    samples: list[str] = field(default_factory=list)
    attribute_label: str | None = None  # filled by the naming call
    uom: str | None = None


@dataclass
class ParseTemplate:
    """A reusable, deterministic parser for one family."""

    family_key: str  # f"{Part_Manuf}::{classpath}"
    slots: list[Slot] = field(default_factory=list)
    support: int = 0  # how many rows it was induced from


def mine_slots(descriptions: list[str]) -> list[Slot]:
    """Pass 2 -- positional and co-occurrence statistics over one family.

    A slot whose value is constant across the family is boilerplate; one that
    varies within a stable shape is a variable field. No dictionary involved.
    """
    raise NotImplementedError("stage-2: slot mining")


def name_slots(
    slots: list[Slot],
    samples: list[str],
    attribute_schema: list[str],
) -> ParseTemplate:
    """Pass 3 -- the single LLM call that maps slot -> attribute label."""
    raise NotImplementedError("stage-2: slot naming")
