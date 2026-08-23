"""
The data contract at the cell level.

Nothing is written to the output sheet unless it can be expressed as a Cell
with a ProvenanceState. There is deliberately no code path that writes a
free-floating string with no state attached - see ProvenanceState.BLANK_FLAGGED
for what happens when nothing supports a value.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProvenanceState(str, Enum):
    PARSED = "PARSED"              # taken verbatim from the input string (character span retained)
    LOOKUP = "LOOKUP"              # matched an approved controlled vocabulary / alias table
    INFERRED = "INFERRED"          # derived from cross-row (sibling) consensus
    RETRIEVED = "RETRIEVED"        # found in an indexed manufacturer document (URL retained)
    BLANK_FLAGGED = "BLANK_FLAGGED"  # nothing supports a value - deliberately left empty


class Evidence(BaseModel):
    """What backs a cell's value. Shape varies by state, so every field is optional."""
    source_field: str | None = None          # e.g. "Part_Desc"
    span: tuple[int, int] | None = None      # character offsets into source_field, for PARSED
    sibling_skus: list[str] | None = None    # contributing MPNs, for INFERRED
    document_url: str | None = None          # for RETRIEVED
    matched_alias: str | None = None         # for LOOKUP (e.g. distributor->manufacturer alias hit)
    note: str | None = None


class Cell(BaseModel):
    value: Any = None
    uom: str | None = None
    state: ProvenanceState = ProvenanceState.BLANK_FLAGGED
    confidence: float = 0.0
    evidence: Evidence = Field(default_factory=Evidence)
    reason: str = ""

    def is_blank(self) -> bool:
        return self.state == ProvenanceState.BLANK_FLAGGED or self.value in (None, "")

    def display_value(self) -> str:
        """What actually gets written into the output CSV cell."""
        if self.is_blank():
            return ""
        return str(self.value)


class AttributeDef(BaseModel):
    """One permitted attribute slot within a classpath's schema."""
    label: str
    uom: str | None = None                # expected/canonical UOM, if the attribute is a measurement
    lov: list[str] | None = None          # controlled vocabulary; None = free-form within the field
    priority: int = 5                     # 1 = always include in compressed descriptions, 10 = drop first
    numeric: bool = False                 # participates in statistical outlier checks


class ClasspathSchema(BaseModel):
    name: str                              # e.g. "Appliances & Consumer Electronics>Kitchen Appliances>Built-In Dishwashers"
    dept: str
    klass: str
    fine: str
    item_type: str                         # goes into MOBILE_DESC / Product Name style fields
    attributes: list[AttributeDef]
    router_keywords: list[str] = Field(default_factory=list)  # Part_Manuf substrings that route here deterministically
    desc_keywords: list[str] = Field(default_factory=list)    # Part_Desc keywords that help disambiguate

    def attribute_labels(self) -> list[str]:
        return [a.label for a in self.attributes]

    def get_attribute(self, label: str) -> AttributeDef | None:
        for a in self.attributes:
            if a.label == label:
                return a
        return None


class ClassificationResult(BaseModel):
    row_index: int
    classpath: str
    method: str        # "router" | "llm" | "fallback"
    confidence: float


class FamilyKey(BaseModel):
    part_manuf: str
    classpath: str

    def key(self) -> str:
        return f"{self.part_manuf}||{self.classpath}"


class EnrichedRecord(BaseModel):
    """Everything CatalogIQ knows about one input row, before final CSV serialization."""
    row_index: int
    mfg_part_num: str
    part_desc: str
    part_manuf: str
    e1_brand: str
    unilog_brand: str
    dib_brand: str

    classpath: str = ""
    classification_confidence: float = 0.0

    # attribute_label -> Cell
    attributes: dict[str, Cell] = Field(default_factory=dict)

    # top-level output fields that aren't in the numbered ATTRIBUTE_* slots
    manufacturer_name: Cell = Field(default_factory=Cell)
    brand_name: Cell = Field(default_factory=Cell)

    mobile_desc: Cell = Field(default_factory=Cell)
    invoice_desc: Cell = Field(default_factory=Cell)
    short_desc: Cell = Field(default_factory=Cell)
    long_desc1: Cell = Field(default_factory=Cell)
    retail_desc: Cell = Field(default_factory=Cell)

    flagged: bool = False
    flag_reasons: list[str] = Field(default_factory=list)

    def all_cells(self) -> dict[str, Cell]:
        out = dict(self.attributes)
        out["MANUFACTURER_NAME"] = self.manufacturer_name
        out["BRAND_NAME"] = self.brand_name
        out["MOBILE_DESC"] = self.mobile_desc
        out["INVOICE_DESC"] = self.invoice_desc
        out["SHORT_DESC"] = self.short_desc
        out["LONG_DESC1"] = self.long_desc1
        out["RETAIL_DESC"] = self.retail_desc
        return out

    def recompute_flags(self) -> None:
        self.flag_reasons = [
            f"{label}: no supporting evidence"
            for label, cell in self.all_cells().items()
            if cell.is_blank() and label in ("MANUFACTURER_NAME",)  # core fields that must not be blank
        ]
        self.flagged = len(self.flag_reasons) > 0
