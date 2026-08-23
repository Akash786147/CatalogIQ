"""The internal representation of every value in the system.

Nothing downstream ever handles a bare string. A value without a provenance
state is never written to output -- that single invariant is what makes the
system architecturally incapable of fabricating content.

See docs/02-data-contract.md.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Provenance(str, Enum):
    """How we came to believe a value.

    There is deliberately no GENERATED tier. If none of these four apply, the
    cell stays empty and gets flagged.
    """

    PARSED = "PARSED"  # read out of the input string, with a character span
    LOOKUP = "LOOKUP"  # matched against a controlled vocabulary
    INFERRED = "INFERRED"  # cross-row consensus, with contributing SKUs
    RETRIEVED = "RETRIEVED"  # manufacturer document, with a URL


class Evidence(BaseModel):
    """Where the value came from, specifically enough for a human to check."""

    source: str  # "Part_Desc", "consensus", a URL, a vocabulary name
    span: tuple[int, int] | None = None  # char offsets, for PARSED
    contributing_skus: list[str] = Field(default_factory=list)  # for INFERRED
    url: str | None = None  # for RETRIEVED
    snippet: str | None = None  # the retrieved text we extracted from


class Cell(BaseModel):
    """One value, plus everything needed to justify it."""

    value: str | None = None
    uom: str | None = None
    state: Provenance | None = None
    confidence: float = 0.0
    evidence: Evidence | None = None
    reason: str | None = None

    @property
    def is_populated(self) -> bool:
        """A cell only counts as populated if it is both non-empty and sourced."""
        return bool(self.value) and self.state is not None

    def as_output(self) -> str:
        """What the 252-column CSV sees. An unsourced cell is blank, always."""
        return self.value if self.is_populated else ""

    @classmethod
    def empty(cls, reason: str | None = None) -> Cell:
        """An honest gap. This is a first-class result, not a failure."""
        return cls(value=None, state=None, confidence=0.0, reason=reason)


class Attribute(BaseModel):
    """One ATTRIBUTE_LABEL / VALUE / UOM triplet.

    The label comes from the classpath schema and is emitted even when the value
    is unknown -- exactly as the ground-truth rows do. The label set is the
    checklist; the blanks are the honest gaps.
    """

    label: str
    cell: Cell = Field(default_factory=Cell)

    @property
    def uom(self) -> str:
        return self.cell.uom or ""


class EnrichedRow(BaseModel):
    """One product, fully processed.

    `fields` holds the flat 252-column values keyed by their exact output header.
    `attributes` holds the ordered triplets, which the writer expands into
    ATTRIBUTE_LABEL/VALUE/UOM 1..50.
    """

    row_id: str
    source: dict[str, str] = Field(default_factory=dict)  # the 6 input columns, verbatim
    classpath: Cell = Field(default_factory=Cell)
    fields: dict[str, Cell] = Field(default_factory=dict)
    attributes: list[Attribute] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)

    def needs_review(self, threshold: float) -> bool:
        if self.flags:
            return True
        return any(c.is_populated and c.confidence < threshold for c in self.iter_cells())

    def iter_cells(self):
        yield self.classpath
        yield from self.fields.values()
        for attr in self.attributes:
            yield attr.cell
