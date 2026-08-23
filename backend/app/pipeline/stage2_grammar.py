"""
Stage 2: the learned abbreviation grammar.

Industrial descriptions are compressed trade shorthand:
    "573352 40W Led Med 27k 2pk"
    -> Wattage 40 W | Lamp Type LED | Base Medium | Color Temp 2700 K | Pack Qty 2

Three passes, matching docs/01-architecture.md:

Pass 1 (tokenize): split each description into typed tokens - a number+unit
pair, an alphanumeric part-code, or a bare word. Pure regex, no model call.

Pass 2 (mine the family): group rows by (Part_Manuf, classpath) and look at
which token shapes recur across the family. A simplification from the
original "positional slot" design: slots are keyed by unit (for NUM_UNIT
tokens) or by recurring-but-varying word (for categorical tokens), rather
than by raw token index. This is more robust to descriptions of different
length within a family, is still mined statistically from the sibling group
rather than hardcoded, and is still testable by holding out an entire
manufacturer (see stage2 tests). Pure computation, no model call.

Pass 3 (name the slots): map each mined slot to an attribute label from the
classpath schema - one call per family via app.llm.template_induction, with
a deterministic heuristic fallback when no API key is configured.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import pandas as pd

from app.core.classpaths import ClasspathSchema, get_classpath
from app.core.schema import Cell, Evidence, ProvenanceState
from app.core.uom import canonical_uom
from app.llm import client
from app.llm.template_induction import name_slots_heuristic, name_slots_llm

_UNIT_ALTS = "W|V|A|K|in|ft|lm|dBA|dba|pk|pc|pcs|lb|lbs"
_NUM_UNIT_RE = re.compile(rf"(\d+(?:\.\d+)?)\s*({_UNIT_ALTS})\b", re.IGNORECASE)
# trade shorthand for dimensions uses the bare quote symbols instead of "in"/"ft"
_QUOTE_UNIT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(\"|')")
_QUOTE_TO_UOM = {'"': "in", "'": "ft"}
_CODE_RE = re.compile(r"\b(?=[A-Za-z0-9]*\d)(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9\-]{4,}\b")
_WORD_RE = re.compile(r"\b[A-Za-z]{2,}\b")


@dataclass
class Token:
    text: str
    type: str  # "NUM_UNIT" | "CODE" | "WORD"
    start: int
    end: int
    value: float | None = None
    unit: str | None = None


def tokenize(desc: str) -> list[Token]:
    tokens: list[Token] = []
    consumed = [False] * len(desc)

    for m in _NUM_UNIT_RE.finditer(desc):
        value = float(m.group(1))
        unit = canonical_uom(m.group(2))
        # trade shorthand: "27k" / "50k" means 2700K / 5000K, not literally 27/50 Kelvin
        if unit == "K" and value < 100:
            value *= 100
        tokens.append(Token(m.group(0), "NUM_UNIT", m.start(), m.end(), value=value, unit=unit))
        for i in range(m.start(), m.end()):
            consumed[i] = True

    for m in _QUOTE_UNIT_RE.finditer(desc):
        if any(consumed[m.start():m.end()]):
            continue
        tokens.append(Token(m.group(0), "NUM_UNIT", m.start(), m.end(),
                             value=float(m.group(1)), unit=_QUOTE_TO_UOM[m.group(2)]))
        for i in range(m.start(), m.end()):
            consumed[i] = True

    for m in _CODE_RE.finditer(desc):
        if any(consumed[m.start():m.end()]):
            continue
        tokens.append(Token(m.group(0), "CODE", m.start(), m.end()))
        for i in range(m.start(), m.end()):
            consumed[i] = True

    for m in _WORD_RE.finditer(desc):
        if any(consumed[m.start():m.end()]):
            continue
        tokens.append(Token(m.group(0), "WORD", m.start(), m.end()))

    tokens.sort(key=lambda t: t.start)
    return tokens


@dataclass
class FamilySlot:
    index: int
    kind: str            # "unit" | "word"
    unit: str | None
    examples: list[str] = field(default_factory=list)


def mine_family_slots(descs: list[str], min_examples: int = 2) -> list[FamilySlot]:
    """Pass 2. Returns candidate slots mined across the family's descriptions."""
    unit_examples: dict[str, list[str]] = defaultdict(list)
    word_counter: Counter = Counter()
    word_examples: dict[str, list[str]] = defaultdict(list)

    for desc in descs:
        seen_units_this_row = set()
        for tok in tokenize(desc):
            if tok.type == "NUM_UNIT" and tok.unit:
                if tok.unit not in seen_units_this_row:
                    unit_examples[tok.unit].append(tok.text)
                    seen_units_this_row.add(tok.unit)
            elif tok.type == "WORD":
                word_counter[tok.text.lower()] += 1
                if len(word_examples[tok.text.lower()]) < 10:
                    word_examples[tok.text.lower()].append(tok.text)

    slots: list[FamilySlot] = []
    idx = 0
    for unit, examples in unit_examples.items():
        if len(examples) >= min_examples:
            slots.append(FamilySlot(index=idx, kind="unit", unit=unit, examples=examples))
            idx += 1

    # a WORD is a candidate categorical slot if it recurs across several rows
    # AND there is more than one distinct such word competing for the role
    # (i.e. it varies row to row rather than being constant brand/model filler)
    n_docs = max(len(descs), 1)
    recurring_words = [w for w, c in word_counter.items() if 2 <= c < n_docs]
    if len(recurring_words) >= 2:
        grouped = Counter()
        for w in recurring_words:
            grouped[w] = word_counter[w]
        for w, _ in grouped.most_common(6):
            slots.append(FamilySlot(index=idx, kind="word", unit=None, examples=word_examples[w]))
            idx += 1

    return slots


def build_families(df: pd.DataFrame, classifications: dict[int, str]) -> dict[str, list[int]]:
    families: dict[str, list[int]] = defaultdict(list)
    for idx, row in df.iterrows():
        classpath = classifications.get(idx, "Unclassified")
        key = f"{row['Part_Manuf']}||{classpath}"
        families[key].append(idx)
    return families


def induce_family_template(family_key: str, row_indices: list[int], df: pd.DataFrame) -> dict[int, str]:
    """Pass 2 + 3 combined for one family. Returns {mined_slot_index: attribute_label}."""
    classpath_name = family_key.split("||", 1)[1]
    schema = get_classpath(classpath_name)
    if not schema.attributes:
        return {}

    descs = [df.at[i, "Part_Desc"] for i in row_indices]
    slots = mine_family_slots(descs)
    if not slots:
        return {}

    mined_slots_payload = [{"index": s.index, "examples": s.examples, "unit": s.unit} for s in slots]

    if client.is_configured():
        try:
            return name_slots_llm(family_key, descs, mined_slots_payload, schema)
        except client.LLMUnavailable:
            pass
    return name_slots_heuristic(mined_slots_payload, schema)


def apply_template_to_row(
    desc: str, slot_mapping: dict[int, str], slots: list[FamilySlot], schema: ClasspathSchema
) -> dict[str, Cell]:
    """Re-extracts each mapped slot's value from THIS row's description, with exact char span."""
    cells: dict[str, Cell] = {}
    tokens = tokenize(desc)

    slots_by_index = {s.index: s for s in slots}

    for slot_index, label in slot_mapping.items():
        slot = slots_by_index.get(slot_index)
        if slot is None:
            continue
        attr = schema.get_attribute(label)
        if attr is None:
            continue

        if slot.kind == "unit" and slot.unit:
            match = next((t for t in tokens if t.type == "NUM_UNIT" and t.unit == slot.unit), None)
            if match:
                cells[label] = Cell(
                    value=match.value, uom=match.unit, state=ProvenanceState.PARSED,
                    confidence=0.95,
                    evidence=Evidence(source_field="Part_Desc", span=(match.start, match.end)),
                    reason=f"parsed from '{match.text}' via family abbreviation template",
                )
        elif slot.kind == "word" and attr.lov:
            from app.core.lov import conform_to_lov
            for tok in tokens:
                if tok.type != "WORD":
                    continue
                matched, score = conform_to_lov(tok.text, attr.lov)
                if matched:
                    cells[label] = Cell(
                        value=matched, state=ProvenanceState.PARSED, confidence=min(0.9, score / 100),
                        evidence=Evidence(source_field="Part_Desc", span=(tok.start, tok.end)),
                        reason=f"parsed token '{tok.text}' matched to LOV '{matched}'",
                    )
                    break

    return cells
