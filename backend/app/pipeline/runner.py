"""Stage orchestration.

This runs end-to-end today. Unimplemented stages return their input unchanged,
which produces a valid 252-column file where every enriched cell is an honest
gap. That is a correct -- if unhelpful -- output, and it means the deliverable
never breaks while stages are being built independently.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.cell import Cell, EnrichedRow, Evidence, Provenance
from app.core.schema import PASSTHROUGH_COLUMNS
from app.io.readers import read_input_rows
from app.io.writers import write_csv, write_provenance
from app.pipeline import classify, compose, consensus, parse, retrieve, validate

log = logging.getLogger(__name__)


def _seed_row(index: int, source: dict[str, str | None]) -> EnrichedRow:
    """Build the starting row: passthrough columns and the two identifiers we
    can assert without any inference."""
    row = EnrichedRow(
        row_id=source.get("Mfg_Part_Num") or f"row-{index}",
        source={col: source.get(col) or "" for col in PASSTHROUGH_COLUMNS},
    )

    mpn = source.get("Mfg_Part_Num")
    if mpn:
        # The only field we can populate with certainty from the input alone.
        row.fields["MANUFACTURER_PART_NUMBER"] = Cell(
            value=mpn,
            state=Provenance.PARSED,
            confidence=1.0,
            evidence=Evidence(source="Mfg_Part_Num"),
            reason="Copied verbatim from the input part number column",
        )
    return row


def run_pipeline(
    input_path: Path,
    output_path: Path,
    provenance_path: Path | None = None,
    limit: int | None = None,
) -> list[EnrichedRow]:
    """Run all seven stages over an input file and write the deliverable.

    Stages 3a and 2's template induction are corpus-level: they need the whole
    batch, not one row, which is why the batch is materialised before enrichment
    rather than streamed.
    """
    rows = [
        _seed_row(i, src)
        for i, src in enumerate(read_input_rows(input_path))
        if limit is None or i < limit
    ]
    log.info("loaded %d rows from %s", len(rows), input_path.name)

    # 1. Classify -- assigns classpath + the attribute schema everything else
    #    is constrained by.
    rows = classify.classify_batch(rows)

    # 2. Parse -- induces one template per (manufacturer x classpath) family,
    #    then applies it deterministically across that family.
    rows = parse.parse_batch(rows)

    # 3a. Consensus -- sparse rows inherit attributes verified across siblings.
    rows = consensus.apply_consensus(rows)

    # 3b. Retrieval -- manufacturer documents only, sourcing rule enforced by
    #     domain allowlist in code.
    rows = retrieve.enrich_from_documents(rows)

    # 4. Validate -- may downgrade confidence or void a value outright.
    rows = validate.validate_batch(rows)

    # 5. Compose -- no LLM. All five descriptions from the one fact layer.
    rows = compose.compose_batch(rows)

    # 6. Emit.
    write_csv(rows, output_path)
    if provenance_path:
        write_provenance(rows, provenance_path)
    log.info("wrote %s", output_path)

    return rows
