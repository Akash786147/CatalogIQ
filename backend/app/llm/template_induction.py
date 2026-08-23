"""
Stage 2, Pass 3: name the mined abbreviation-grammar slots.

Given a family's sample descriptions and the mined positional slot structure
(from app.pipeline.stage2_grammar), map each slot to an attribute label from
the classpath's schema. One call per FAMILY (manufacturer x classpath), not
per row - this is what keeps cost per 1,000 SKUs low.

If the LLM is unavailable, falls back to a deterministic heuristic: unit
suffixes (W, K, pk, in, V, A) map directly to the matching numeric attribute
by unit; the first free alphabetic token is matched fuzzily against LOV
values across the schema's categorical attributes. This keeps the pipeline
fully runnable with zero API key, at reduced (but nonzero) coverage - a
deliberate degrade-gracefully design, not a placeholder.
"""
from __future__ import annotations

from app.core.lov import conform_to_lov
from app.core.schema import AttributeDef, ClasspathSchema
from app.llm import client

UNIT_TO_ATTRIBUTE_UOM = {
    "W": "W", "K": "K", "V": "V", "A": "A", "IN": "in", "FT": "ft", "DBA": "dBA", "LM": "lm",
}


def name_slots_llm(
    family_key: str,
    sample_descs: list[str],
    mined_slots: list[dict],
    schema: ClasspathSchema,
) -> dict[int, str]:
    """Returns {slot_index: attribute_label}. Raises LLMUnavailable if no key configured."""
    attr_list = "\n".join(f"- {a.label}" + (f" (unit: {a.uom})" if a.uom else "") for a in schema.attributes)
    slots_desc = "\n".join(
        f"slot {s['index']}: example values {s['examples'][:5]}" for s in mined_slots
    )
    system = (
        "You are naming the columns of a mined parsing template for abbreviated industrial "
        "product descriptions. Map each numbered slot to ONE attribute label from the allowed "
        "list, or null if no attribute fits. Respond with JSON only: "
        '{"slot_mapping": {"<slot_index>": "<attribute label or null>", ...}}'
    )
    user = (
        f"Sample descriptions from this family:\n" + "\n".join(sample_descs[:10]) + "\n\n"
        f"Mined slots:\n{slots_desc}\n\n"
        f"Allowed attribute labels:\n{attr_list}"
    )
    result = client.complete_json(system, user, max_tokens=400)
    mapping = result.get("slot_mapping", {})
    valid_labels = {a.label for a in schema.attributes}
    out: dict[int, str] = {}
    for k, v in mapping.items():
        if v and v in valid_labels:
            try:
                out[int(k)] = v
            except ValueError:
                continue
    return out


def name_slots_heuristic(mined_slots: list[dict], schema: ClasspathSchema) -> dict[int, str]:
    """Deterministic fallback: no model call, no API key required."""
    out: dict[int, str] = {}
    used_labels: set[str] = set()

    numeric_by_uom: dict[str, AttributeDef] = {
        a.uom: a for a in schema.attributes if a.uom and a.numeric
    }
    categorical_attrs = [a for a in schema.attributes if a.lov]

    for slot in mined_slots:
        unit = slot.get("unit")
        if unit and unit.upper() in UNIT_TO_ATTRIBUTE_UOM:
            canon = UNIT_TO_ATTRIBUTE_UOM[unit.upper()]
            attr = numeric_by_uom.get(canon)
            if attr and attr.label not in used_labels:
                out[slot["index"]] = attr.label
                used_labels.add(attr.label)
                continue

        # try matching a categorical LOV against the most common example value
        examples = slot.get("examples", [])
        if examples and categorical_attrs:
            best_attr, best_score = None, 0.0
            for attr in categorical_attrs:
                if attr.label in used_labels or not attr.lov:
                    continue
                _, score = conform_to_lov(str(examples[0]), attr.lov)
                if score > best_score:
                    best_attr, best_score = attr, score
            if best_attr and best_score >= 85:
                out[slot["index"]] = best_attr.label
                used_labels.add(best_attr.label)

    return out
