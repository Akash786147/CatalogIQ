"""
Input loading. Placeholder scrubbing happens here, once, on ingest - so
downstream code never has to special-case "-- Unbranded --" style strings.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_INPUT_COLUMNS = [
    "Mfg_Part_Num", "Part_Desc", "E1_Brand", "Unilog_Brand", "DIB_Brand", "Part_Manuf",
]

PLACEHOLDER_TOKENS = {
    "-- unbranded --",
    "-- no unilog brand --",
    "-- no dib brand --",
    "-",
    "",
}


def _scrub_placeholder(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in PLACEHOLDER_TOKENS else text


def load_input_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [c for c in REQUIRED_INPUT_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Input CSV missing required columns: {missing}")

    for col in ["E1_Brand", "Unilog_Brand", "DIB_Brand", "Part_Manuf"]:
        df[col] = df[col].map(_scrub_placeholder)
    df["Part_Desc"] = df["Part_Desc"].fillna("").astype(str)
    df["Mfg_Part_Num"] = df["Mfg_Part_Num"].fillna("").astype(str)
    df = df.reset_index(drop=True)
    return df


def load_output_header(delivery_format_csv: Path) -> list[str]:
    """The 252 output column names, in the exact required order. Never modified."""
    header_df = pd.read_csv(delivery_format_csv, nrows=0)
    return list(header_df.columns)


def load_spec_corpus(corpus_dir: Path) -> list[dict]:
    """
    Optional manufacturer spec-sheet corpus for the RAG enrichment stage.
    Each .txt file: first line is the source URL, rest is the document body.
    Returns [] if the directory doesn't exist or is empty - that's an honest
    gap, not an error (Stage 3b simply has nothing to retrieve from).
    """
    docs = []
    if not corpus_dir.exists():
        return docs
    for fp in sorted(corpus_dir.glob("*.txt")):
        text = fp.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        if not lines:
            continue
        url = lines[0].strip()
        body = "\n".join(lines[1:])
        docs.append({"manufacturer_hint": fp.stem.split("__")[0], "url": url, "text": body})
    return docs
