"""
Stage 7: correction propagation. A reviewer edit is stored as a RULE, not a
one-off cell patch - so fixing one distributor->manufacturer mapping error
can be reported as "applied to 55 rows", and reapplied automatically on the
next run of the same batch.

Persisted to SQLite (data/output/corrections.db) per docs/01-architecture.md.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core.schema import EnrichedRecord


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS correction_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope_field TEXT NOT NULL,
            scope_value TEXT NOT NULL,
            target_field TEXT NOT NULL,
            new_value TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def add_correction_rule(
    db_path: Path, scope_field: str, scope_value: str, target_field: str, new_value: str
) -> int:
    conn = _connect(db_path)
    cur = conn.execute(
        "INSERT INTO correction_rules (scope_field, scope_value, target_field, new_value) VALUES (?, ?, ?, ?)",
        (scope_field, scope_value, target_field, new_value),
    )
    conn.commit()
    rule_id = cur.lastrowid
    conn.close()
    return rule_id


def load_correction_rules(db_path: Path) -> list[dict]:
    if not db_path.exists():
        return []
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT scope_field, scope_value, target_field, new_value FROM correction_rules"
    ).fetchall()
    conn.close()
    return [
        {"scope_field": r[0], "scope_value": r[1], "target_field": r[2], "new_value": r[3]}
        for r in rows
    ]


SCOPE_TO_RECORD_FIELD = {
    "Part_Manuf": "part_manuf",
    "Mfg_Part_Num": "mfg_part_num",
    "Classpath": "classpath",
}

TARGET_TO_CELL_FIELD = {
    "MANUFACTURER_NAME": "manufacturer_name",
    "BRAND_NAME": "brand_name",
}


def apply_correction_rules(records: list[EnrichedRecord], rules: list[dict]) -> dict[str, int]:
    """Applies all rules to matching records in place. Returns {rule_summary: affected_count}."""
    from app.core.schema import Cell, Evidence, ProvenanceState

    affected: dict[str, int] = {}
    for rule in rules:
        scope_attr = SCOPE_TO_RECORD_FIELD.get(rule["scope_field"])
        target_attr = TARGET_TO_CELL_FIELD.get(rule["target_field"])
        if not scope_attr or not target_attr:
            continue
        count = 0
        for record in records:
            if getattr(record, scope_attr, None) == rule["scope_value"]:
                setattr(record, target_attr, Cell(
                    value=rule["new_value"], state=ProvenanceState.LOOKUP, confidence=1.0,
                    evidence=Evidence(note="applied from reviewer correction rule"),
                    reason=f"reviewer correction: {rule['scope_field']}='{rule['scope_value']}' -> {rule['target_field']}",
                ))
                count += 1
        summary = f"{rule['scope_field']}='{rule['scope_value']}' -> {rule['target_field']}='{rule['new_value']}'"
        affected[summary] = count
    return affected
