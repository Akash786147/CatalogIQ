"""
The reviewer-UI API.

The CLI remains the primary, evaluated entrypoint (app/cli.py). This module
exists so the React reviewer queue has something to call, and it serves the
UI's contract rather than the pipeline's internal shape - the adaptation from
EnrichedRecord to the wire format happens here, in one place, so neither side
has to know about the other's field names.

Endpoints (all mounted under /api):
    GET  /api/runs/latest      run-level statistics
    POST /api/runs             re-run the pipeline over the configured input
    GET  /api/rows             the review queue, filterable
    GET  /api/rows/{row_id}    one product with full provenance
    POST /api/corrections      save a reviewer correction as a propagating rule
    GET  /api/search           raw vs enriched search comparison
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import get_settings
from app.core.classpaths import get_classpath
from app.core.schema import Cell, EnrichedRecord, ProvenanceState
from app.io.readers import load_input_csv
from app.llm.client import active_provider, usage_log
from app.pipeline import stage7_corrections as corrections
from app.pipeline.run import enrich_dataframe

router = APIRouter(prefix="/api")

# Analyst baseline from docs/00-brief.md: ~15 SKUs per analyst per 8-hour day.
SKUS_PER_ANALYST_DAY = 15
HOURS_PER_DAY = 8

# Cells whose confidence falls below this go to the review queue.
CONFIDENCE_THRESHOLD = 0.85

# The fixed (non-numbered) output fields the reviewer actually adjudicates.
FIXED_FIELDS: list[tuple[str, str]] = [
    ("MANUFACTURER_NAME", "manufacturer_name"),
    ("BRAND_NAME", "brand_name"),
    ("MOBILE_DESC", "mobile_desc"),
    ("INVOICE_DESC", "invoice_desc"),
    ("SHORT_DESC", "short_desc"),
    ("LONG_DESC1", "long_desc1"),
    ("RETAIL_DESC", "retail_desc"),
]


# --------------------------------------------------------------------------
# Run store
# --------------------------------------------------------------------------

class RunStore:
    """Holds the most recent pipeline run in memory.

    The pipeline takes ~3s over the 1,000-row sample with no LLM configured,
    so running it lazily on first request is cheaper than persisting and
    reloading a serialized run.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.records: list[EnrichedRecord] = []
        self.raw_rows: list[dict] = []
        self.stats: dict = {}
        self.input_name: str = ""
        self.completed_at: str = ""
        self.runtime_seconds: float = 0.0

    @property
    def loaded(self) -> bool:
        return bool(self.records)

    def run(self) -> None:
        settings = get_settings()
        input_path = settings.input_csv
        if not input_path.exists():
            raise HTTPException(
                503, f"No input CSV at {input_path}. Place one there or POST /api/runs."
            )
        with self._lock:
            t0 = time.time()
            df = load_input_csv(input_path)
            records, stats = enrich_dataframe(df)

            # Reviewer corrections saved from a previous session apply on every run.
            rules = corrections.load_correction_rules(settings.output_dir / "corrections.db")
            if rules:
                corrections.apply_correction_rules(records, rules)

            self.records = records
            self.raw_rows = df.to_dict("records")
            self.stats = stats
            self.input_name = input_path.name
            self.completed_at = datetime.now(timezone.utc).isoformat()
            self.runtime_seconds = round(time.time() - t0, 2)

    def ensure(self) -> None:
        if not self.loaded:
            self.run()

    def find(self, row_id: str) -> tuple[EnrichedRecord, dict]:
        self.ensure()
        for record, raw in zip(self.records, self.raw_rows):
            if _row_id(record) == row_id:
                return record, raw
        raise HTTPException(404, f"No row {row_id!r} in the current run")


store = RunStore()


def _row_id(record: EnrichedRecord) -> str:
    return record.mfg_part_num or f"row-{record.row_index}"


# --------------------------------------------------------------------------
# Wire format - adapts EnrichedRecord to what the UI expects
# --------------------------------------------------------------------------

def _cell_json(cell: Cell) -> dict[str, Any]:
    """A Cell as the UI sees it.

    BLANK_FLAGGED becomes a null state, because on the UI side "no state" is
    what marks an honest gap - a cell it must render as an explained blank
    rather than as a value.
    """
    blank = cell.is_blank()
    ev = cell.evidence
    evidence = None
    if not blank and (ev.source_field or ev.span or ev.sibling_skus or ev.document_url):
        evidence = {
            "source": ev.source_field or ev.matched_alias or "derived",
            "span": list(ev.span) if ev.span else None,
            "contributing_skus": ev.sibling_skus or [],
            "url": ev.document_url,
            "snippet": ev.note,
        }
    return {
        "value": None if blank else str(cell.value),
        "uom": cell.uom or None,
        "state": None if blank else cell.state.value,
        "confidence": round(cell.confidence, 3),
        "evidence": evidence,
        "reason": cell.reason or None,
    }


def _row_json(record: EnrichedRecord, raw: dict) -> dict[str, Any]:
    fields = {name: _cell_json(getattr(record, attr)) for name, attr in FIXED_FIELDS}

    # The part number is the one field we can assert with certainty from input.
    if record.mfg_part_num:
        fields["MANUFACTURER_PART_NUMBER"] = {
            "value": record.mfg_part_num,
            "uom": None,
            "state": "PARSED",
            "confidence": 1.0,
            "evidence": {"source": "Mfg_Part_Num", "span": None, "contributing_skus": [], "url": None, "snippet": None},
            "reason": "Copied verbatim from the input part number column",
        }

    return {
        "row_id": _row_id(record),
        "source": {
            "Mfg_Part_Num": raw.get("Mfg_Part_Num", ""),
            "Part_Desc": raw.get("Part_Desc", ""),
            "E1_Brand": raw.get("E1_Brand", ""),
            "Unilog_Brand": raw.get("Unilog_Brand", ""),
            "DIB_Brand": raw.get("DIB_Brand", ""),
            "Part_Manuf": raw.get("Part_Manuf", ""),
        },
        "classpath": {
            "value": record.classpath or None,
            "uom": None,
            "state": "LOOKUP" if record.classpath and record.classpath != "Unclassified" else None,
            "confidence": round(record.classification_confidence, 3),
            "evidence": None,
            "reason": None,
        },
        "fields": fields,
        "attributes": [
            {"label": label, "cell": _cell_json(cell)} for label, cell in record.attributes.items()
        ],
        "flags": record.flag_reasons,
    }


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

@router.post("/runs")
def trigger_run() -> dict:
    store.run()
    return {"status": "ok", "rows": len(store.records), "runtime_seconds": store.runtime_seconds}


@router.get("/runs/latest")
def latest_run() -> dict:
    store.ensure()
    records = store.records
    n = len(records)

    provenance_counts = {s.value: 0 for s in ProvenanceState if s != ProvenanceState.BLANK_FLAGGED}
    provenance_counts["GAP"] = 0
    histogram = [0] * 10
    populated = 0
    lov_checked = lov_conforming = 0
    invoice_violations = 0

    for record in records:
        schema = get_classpath(record.classpath)
        for label, cell in record.all_cells().items():
            if cell.is_blank():
                provenance_counts["GAP"] += 1
                continue
            populated += 1
            provenance_counts[cell.state.value] += 1
            bucket = min(int(cell.confidence * 10), 9)
            histogram[bucket] += 1

            # LOV conformance is only meaningful where the schema defines one.
            attr = schema.get_attribute(label) if schema else None
            if attr and attr.lov:
                lov_checked += 1
                if str(cell.value) in attr.lov:
                    lov_conforming += 1

        if len(record.invoice_desc.display_value()) > 40:
            invoice_violations += 1

    flagged = sum(1 for r in records if r.flagged)
    clean = n - flagged
    # Total cells the delivery format has room for, so fill rate is honest
    # about the whole sheet rather than only the columns we attempt.
    cells_total = sum(len(r.all_cells()) for r in records)

    return {
        "run_id": f"run_{store.completed_at[:19].replace(':', '').replace('-', '')}",
        "input_file": store.input_name,
        "completed_at": store.completed_at,
        "rows_total": n,
        "rows_clean": clean,
        "rows_needing_review": flagged,
        "cells_total": cells_total,
        "cells_populated": populated,
        "provenance_counts": provenance_counts,
        "confidence_histogram": histogram,
        "lov_conformance": round(lov_conforming / lov_checked, 3) if lov_checked else 1.0,
        "char_limit_compliance": round(1 - invoice_violations / n, 3) if n else 1.0,
        "llm_calls": len(usage_log),
        "llm_input_tokens": sum(u.get("input_tokens", 0) for u in usage_log),
        "llm_output_tokens": sum(u.get("output_tokens", 0) for u in usage_log),
        "llm_provider": active_provider(),
        "runtime_seconds": store.runtime_seconds,
        "analyst_hours_saved": round(clean / SKUS_PER_ANALYST_DAY * HOURS_PER_DAY),
    }


@router.get("/rows")
def list_rows(
    search: str = Query("", description="Matches part number or description"),
    manufacturer: str = Query("", description="Exact Part_Manuf value"),
    flag: str = Query("", description="Only rows carrying this flag"),
    max_confidence: float | None = Query(None, description="Only rows whose weakest value is at or below this"),
    limit: int = Query(200, le=2000),
) -> list[dict]:
    store.ensure()
    term = search.lower().strip()
    out: list[dict] = []

    for record, raw in zip(store.records, store.raw_rows):
        if manufacturer and raw.get("Part_Manuf", "") != manufacturer:
            continue
        if flag and flag not in record.flag_reasons:
            continue
        if term:
            haystack = " ".join(
                [record.mfg_part_num, record.part_desc, raw.get("Part_Manuf", "")]
            ).lower()
            if term not in haystack:
                continue
        if max_confidence is not None:
            scores = [c.confidence for c in record.all_cells().values() if not c.is_blank()]
            if scores and min(scores) > max_confidence:
                continue
        out.append(_row_json(record, raw))
        if len(out) >= limit:
            break

    # Most-doubtful first: flagged rows rise, then lowest confidence.
    def weakest(row: dict) -> float:
        scores = [a["cell"]["confidence"] for a in row["attributes"] if a["cell"]["value"]]
        return min(scores) if scores else 1.0

    out.sort(key=lambda r: (-len(r["flags"]), weakest(r)))
    return out


@router.get("/rows/{row_id}")
def get_row(row_id: str) -> dict:
    record, raw = store.find(row_id)
    return _row_json(record, raw)


class CorrectionIn(BaseModel):
    rowId: str
    field: str
    value: str
    scopeField: str
    scopeValue: str


@router.post("/corrections")
def submit_correction(body: CorrectionIn) -> dict:
    """A reviewer edit is stored as a RULE, not a one-off cell patch.

    That is what lets one fix report "applied to 55 rows" instead of being
    re-made 55 times.
    """
    store.ensure()
    settings = get_settings()
    db_path = settings.output_dir / "corrections.db"

    rule_id = corrections.add_correction_rule(
        db_path,
        scope_field=body.scopeField,
        scope_value=body.scopeValue,
        target_field=body.field,
        new_value=body.value,
    )

    rules = corrections.load_correction_rules(db_path)
    applied = corrections.apply_correction_rules(store.records, rules)
    affected = applied.get(f"{body.scopeField}={body.scopeValue}", 0) or sum(applied.values())

    # Descriptions are composed from the fact layer, so a corrected fact
    # dirties them - those rows need a re-check.
    rereview = 0
    sample: list[str] = []
    for record, raw in zip(store.records, store.raw_rows):
        if raw.get(body.scopeField, "") == body.scopeValue:
            if len(sample) < 5:
                sample.append(_row_id(record))
            if not record.mobile_desc.is_blank() or not record.short_desc.is_blank():
                rereview += 1

    return {
        "rule": {
            "id": str(rule_id),
            "scope_field": body.scopeField,
            "scope_value": body.scopeValue,
            "field": body.field,
            "value": body.value,
            "author": "reviewer",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "rows_affected": affected,
            "rows_needing_rereview": rereview,
        },
        "rows_affected": affected,
        "rows_needing_rereview": rereview,
        "sample_row_ids": sample,
    }


@router.get("/search")
def compare_search(q: str = Query(..., min_length=1)) -> dict:
    """The commercial case in one query: the same search over raw vs enriched content.

    Raw searches only the original Part_Desc, which is trade shorthand. Enriched
    searches the validated attribute layer plus the composed descriptions.
    """
    store.ensure()
    terms = [t for t in q.lower().split() if t]

    raw_hits: list[dict] = []
    enriched_hits: list[dict] = []

    for record, raw in zip(store.records, store.raw_rows):
        raw_text = f"{record.mfg_part_num} {record.part_desc}".lower()
        if all(t in raw_text for t in terms) and len(raw_hits) < 10:
            raw_hits.append({
                "row_id": _row_id(record),
                "title": record.part_desc,
                "manufacturer": raw.get("Part_Manuf", ""),
                "matched_on": ["Part_Desc"],
            })

        matched: list[str] = []
        searchable: list[str] = [record.short_desc.display_value().lower()]
        for label, cell in record.attributes.items():
            if cell.is_blank():
                continue
            blob = f"{cell.value} {cell.uom or ''}".lower()
            searchable.append(f"{label.lower()} {blob}")
            if any(t in blob for t in terms):
                matched.append(label)

        haystack = " ".join(searchable)
        if all(t in haystack for t in terms) and len(enriched_hits) < 10:
            enriched_hits.append({
                "row_id": _row_id(record),
                "title": record.short_desc.display_value() or record.part_desc,
                "manufacturer": record.manufacturer_name.display_value() or raw.get("Part_Manuf", ""),
                "matched_on": matched[:4] or ["Description"],
            })

    return {"query": q, "raw": raw_hits, "enriched": enriched_hits}


@router.get("/manufacturers")
def list_manufacturers() -> list[str]:
    store.ensure()
    return sorted({r.get("Part_Manuf", "") for r in store.raw_rows if r.get("Part_Manuf")})


@router.get("/flags")
def list_flags() -> list[str]:
    store.ensure()
    return sorted({f for r in store.records for f in r.flag_reasons})
