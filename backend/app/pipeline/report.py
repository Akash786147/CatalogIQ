"""
The run report: coverage by category, confidence distribution, LOV
conformance proxy, INVOICE_DESC compliance, cost/runtime. This is what gets
put on the slide (docs/05-evaluation.md).
"""
from __future__ import annotations

from collections import defaultdict

from app.core.schema import EnrichedRecord, ProvenanceState
from app.llm.client import usage_log


def build_run_report(records: list[EnrichedRecord], stats: dict) -> dict:
    n = len(records)
    state_counts: dict[str, int] = defaultdict(int)
    coverage_by_classpath: dict[str, dict] = defaultdict(lambda: {"total": 0, "populated": 0})
    confidences: list[float] = []
    invoice_violations = 0

    for r in records:
        cov = coverage_by_classpath[r.classpath]
        for cell in r.attributes.values():
            state_counts[cell.state.value] += 1
            cov["total"] += 1
            if not cell.is_blank():
                cov["populated"] += 1
                confidences.append(cell.confidence)
        if len(r.invoice_desc.display_value()) > 40:
            invoice_violations += 1

    coverage_pct = {
        cp: round(v["populated"] / v["total"], 3) if v["total"] else 0.0
        for cp, v in coverage_by_classpath.items()
    }

    manufacturer_resolved = sum(1 for r in records if not r.manufacturer_name.is_blank())

    total_input_tokens = sum(u["input_tokens"] for u in usage_log)
    total_output_tokens = sum(u["output_tokens"] for u in usage_log)
    # Claude pricing varies by model/tier; report raw token counts rather than a dollar
    # figure we can't verify - see docs/05-evaluation.md for how to price these per model.

    return {
        "rows_processed": n,
        "runtime_seconds": stats.get("runtime_seconds"),
        "classification_method_counts": stats.get("classification_method_counts"),
        "classpath_counts": stats.get("classpath_counts"),
        "attribute_cell_state_counts": dict(state_counts),
        "coverage_by_classpath": coverage_pct,
        "manufacturer_resolved_pct": round(manufacturer_resolved / n, 3) if n else 0.0,
        "flagged_rows": stats.get("flagged_rows"),
        "flagged_row_pct": round(stats.get("flagged_rows", 0) / n, 3) if n else 0.0,
        "invoice_desc_char_limit_violations": invoice_violations,
        "mean_confidence_nonblank_cells": round(sum(confidences) / len(confidences), 3) if confidences else 0.0,
        "llm_calls": len(usage_log),
        "llm_input_tokens": total_input_tokens,
        "llm_output_tokens": total_output_tokens,
    }
