"""
Stage 1B: LLM classification fallback for rows Stage A's deterministic router
couldn't place. The candidate set is the full registered classpath list
(small - a dozen or so categories), so this is a direct pick rather than a
retrieval problem; if the catalogue of classpaths grows much larger, swap in
an embedding-based candidate shortlist ahead of this call (see docs/04-decisions.md
for why that wasn't built now).
"""
from __future__ import annotations

from app.core.classpaths import all_classpaths
from app.core.schema import ClassificationResult
from app.llm import client


def classify_row_llm(row_index: int, part_desc: str, part_manuf: str) -> ClassificationResult:
    candidates = all_classpaths()
    options = "\n".join(f"- {c.name} (item type: {c.item_type})" for c in candidates)

    system = (
        "You classify one industrial-distribution product row into exactly one classpath "
        "from a fixed list. Respond with JSON only: {\"classpath\": \"<exact name from the list>\", "
        "\"confidence\": <0-1 float>}. If nothing fits reasonably, use \"Unclassified\" with low confidence. "
        "Never invent a classpath name not in the list."
    )
    user = (
        f"Part_Desc: {part_desc}\n"
        f"Part_Manuf (distributor): {part_manuf}\n\n"
        f"Candidate classpaths:\n{options}"
    )

    result = client.complete_json(system, user, max_tokens=150)
    classpath = result.get("classpath", "Unclassified")
    confidence = float(result.get("confidence", 0.0))

    valid_names = {c.name for c in candidates}
    if classpath not in valid_names:
        classpath = "Unclassified"
        confidence = 0.0

    return ClassificationResult(row_index=row_index, classpath=classpath, method="llm", confidence=confidence)
