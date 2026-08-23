"""
Thin FastAPI wrapper around the same pipeline the CLI runs. This exists so
a review UI (out of scope for this build - see README) has something to
call; the CLI in app/cli.py is the primary, evaluated entrypoint and does
not depend on this server running.
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.api.routes import router as api_router
from app.config import get_settings
from app.io.readers import REQUIRED_INPUT_COLUMNS, load_output_header
from app.io.readers import _scrub_placeholder  # noqa: F401 - reused for API-path scrubbing
from app.io.writers import write_output, write_provenance
from app.llm.client import active_provider, is_configured
from app.pipeline import stage7_corrections as corrections
from app.pipeline.report import build_run_report
from app.pipeline.run import enrich_dataframe

app = FastAPI(title="CatalogIQ", version="0.1.0")

# The Vite dev server proxies /api, so this only matters when the frontend is
# served from a different origin (a built bundle on another port, say).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# The reviewer-UI endpoints (/api/...). The CLI remains the evaluated entrypoint.
app.include_router(api_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "llm_configured": is_configured(),
        "llm_provider": active_provider(),
    }


@app.post("/enrich")
async def enrich_endpoint(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Expected a CSV file")

    raw_bytes = await file.read()
    df = pd.read_csv(io.BytesIO(raw_bytes), dtype=str, keep_default_na=False)
    missing = [c for c in REQUIRED_INPUT_COLUMNS for c in [c] if c not in df.columns]
    if missing:
        raise HTTPException(400, f"Missing required columns: {missing}")

    for col in ["E1_Brand", "Unilog_Brand", "DIB_Brand", "Part_Manuf"]:
        df[col] = df[col].map(_scrub_placeholder)
    df["Part_Desc"] = df["Part_Desc"].fillna("").astype(str)
    df["Mfg_Part_Num"] = df["Mfg_Part_Num"].fillna("").astype(str)
    df = df.reset_index(drop=True)

    settings = get_settings()
    header = load_output_header(settings.delivery_format_csv)
    records, stats = enrich_dataframe(df)

    db_path = settings.output_dir / "corrections.db"
    rules = corrections.load_correction_rules(db_path)
    if rules:
        corrections.apply_correction_rules(records, rules)

    raw_rows = df.to_dict("records")
    out_df = pd.DataFrame(
        [_row_dict(r, header, raw) for r, raw in zip(records, raw_rows)], columns=header
    )
    buf = io.StringIO()
    out_df.to_csv(buf, index=False)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=enriched.csv"},
    )


def _row_dict(record, header, raw_row):
    from app.io.writers import _row_to_output_dict
    return _row_to_output_dict(record, header, raw_row)


@app.get("/run-report")
def run_report_endpoint():
    """Returns the most recently written run report, if one exists on disk."""
    settings = get_settings()
    report_path = settings.output_dir / "run_report.json"
    if not report_path.exists():
        raise HTTPException(404, "No run report on disk yet - run the CLI `enrich` command with --report first")
    import json
    return json.loads(report_path.read_text())
