"""
Manufacturer/brand resolution. Part_Manuf is a distributor code, not a
manufacturer - copying it into MANUFACTURER_NAME fails on effectively every
row (see app/core/manufacturer_aliases.py for the proof: the same distributor
code resolves to different manufacturers depending on the product).

Resolution order (source order matters - first hit wins, never overwritten):
  1. Brand token found directly in Part_Desc (PARSED-equivalent confidence -
     the evidence is the product's own description).
  2. E1_Brand / DIB_Brand fields, when not a placeholder (LOOKUP).
  3. Distributor code, ONLY for codes that are unambiguous in the alias table
     (LOOKUP, lower confidence than #1).
  4. Nothing: BLANK_FLAGGED. Never guessed from the distributor code alone
     when the code is known to be ambiguous (e.g. APPDE).
"""
from __future__ import annotations

from app.core.manufacturer_aliases import (
    resolve_brand_from_description,
    resolve_brand_from_distributor,
)
from app.core.schema import Cell, Evidence, ProvenanceState


def resolve_manufacturer_and_brand(
    part_desc: str, part_manuf: str, e1_brand: str, dib_brand: str
) -> tuple[Cell, Cell]:
    hit = resolve_brand_from_description(part_desc)
    if hit:
        manufacturer, brand = hit
        return (
            Cell(value=manufacturer, state=ProvenanceState.PARSED, confidence=0.9,
                 evidence=Evidence(source_field="Part_Desc", note="brand token found in description"),
                 reason="brand token recognized directly in Part_Desc"),
            Cell(value=brand, state=ProvenanceState.PARSED, confidence=0.9,
                 evidence=Evidence(source_field="Part_Desc"),
                 reason="brand token recognized directly in Part_Desc"),
        )

    # E1_Brand / DIB_Brand are BRAND fields by name - they are evidence for BRAND_NAME
    # only, never for MANUFACTURER_NAME (a brand string is not proof of the legal
    # manufacturing entity - Frigidaire(R)/Rheem Manufacturing in the ground truth is
    # exactly this distinction). Try the distributor-code manufacturer mapping
    # independently; if that also fails, manufacturer stays honestly BLANK_FLAGGED
    # even when we do know the brand.
    brand_cell = None
    for field_name, field_value in (("E1_Brand", e1_brand), ("DIB_Brand", dib_brand)):
        if field_value:
            brand_cell = Cell(value=field_value, state=ProvenanceState.LOOKUP, confidence=0.6,
                               evidence=Evidence(source_field=field_name),
                               reason=f"taken from non-placeholder {field_name}")
            break

    dist_hit = resolve_brand_from_distributor(part_manuf)
    if brand_cell:
        if dist_hit:
            manufacturer_value, _ = dist_hit
            manufacturer_cell = Cell(
                value=manufacturer_value, state=ProvenanceState.LOOKUP, confidence=0.55,
                evidence=Evidence(source_field="Part_Manuf", matched_alias=part_manuf),
                reason="distributor code has an unambiguous manufacturer mapping",
            )
        else:
            manufacturer_cell = Cell(
                state=ProvenanceState.BLANK_FLAGGED,
                reason=f"brand known ('{brand_cell.value}') but manufacturer entity unresolved - "
                       f"'{part_manuf}' is a distributor, not proof of the legal manufacturer",
            )
        return manufacturer_cell, brand_cell

    if dist_hit:
        manufacturer, brand = dist_hit
        return (
            Cell(value=manufacturer, state=ProvenanceState.LOOKUP, confidence=0.55,
                 evidence=Evidence(source_field="Part_Manuf", matched_alias=part_manuf),
                 reason="distributor code has an unambiguous manufacturer mapping"),
            Cell(value=brand, state=ProvenanceState.LOOKUP, confidence=0.55,
                 evidence=Evidence(source_field="Part_Manuf", matched_alias=part_manuf),
                 reason="distributor code has an unambiguous manufacturer mapping"),
        )

    return (
        Cell(state=ProvenanceState.BLANK_FLAGGED,
             reason=f"'{part_manuf}' is a distributor, not a manufacturer, and no brand "
                    f"token was found in the description - ambiguous, left for review"),
        Cell(state=ProvenanceState.BLANK_FLAGGED,
             reason="manufacturer unresolved"),
    )
