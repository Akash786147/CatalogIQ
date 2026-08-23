"""
The orchestrator. Ties stages 1-6 together into one call: enrich_dataframe().
Stage 7 (corrections) is applied separately via the CLI `correct` command,
since it operates on an already-completed run.
"""
from __future__ import annotations

import time
from collections import defaultdict

import pandas as pd

from app.config import get_settings
from app.core.classpaths import get_classpath
from app.core.schema import Cell, EnrichedRecord, ProvenanceState
from app.pipeline import stage4_validate as validate
from app.pipeline import stage5_compose as compose
from app.pipeline.manufacturer_resolve import resolve_manufacturer_and_brand
from app.pipeline.stage1_classify import classify_dataframe
from app.pipeline.stage2_grammar import (
    apply_template_to_row,
    build_families,
    induce_family_template,
    mine_family_slots,
)
from app.pipeline.stage3_enrich import cross_row_consensus, retrieval_enrich
from app.pipeline.stage6_provenance import apply_calibration


def enrich_dataframe(df: pd.DataFrame, verbose: bool = False) -> tuple[list[EnrichedRecord], dict]:
    t0 = time.time()
    stats = {"n_rows": len(df)}

    # ---- Stage 1: classification ----
    classifications = classify_dataframe(df)
    classpath_by_idx = {c.row_index: c.classpath for c in classifications}
    confidence_by_idx = {c.row_index: c.confidence for c in classifications}
    stats["classification_method_counts"] = dict(
        pd.Series([c.method for c in classifications]).value_counts()
    )

    # ---- Stage 2: abbreviation grammar, per family ----
    families = build_families(df, classpath_by_idx)
    parsed_attrs_by_idx: dict[int, dict[str, Cell]] = defaultdict(dict)
    family_slot_cache: dict[str, tuple[list, dict]] = {}

    for family_key, row_indices in families.items():
        classpath_name = family_key.split("||", 1)[1]
        schema = get_classpath(classpath_name)
        if not schema.attributes:
            continue
        descs = [df.at[i, "Part_Desc"] for i in row_indices]
        slots = mine_family_slots(descs)
        mapping = induce_family_template(family_key, row_indices, df)
        family_slot_cache[family_key] = (slots, mapping)

        for idx in row_indices:
            desc = df.at[idx, "Part_Desc"]
            cells = apply_template_to_row(desc, mapping, slots, schema)
            parsed_attrs_by_idx[idx].update(cells)

    # ---- Stage 3a: cross-row consensus, per family ----
    for family_key, row_indices in families.items():
        classpath_name = family_key.split("||", 1)[1]
        schema = get_classpath(classpath_name)
        if not schema.attributes or len(row_indices) < 2:
            continue
        family_records = [(df.at[i, "Mfg_Part_Num"], parsed_attrs_by_idx[i]) for i in row_indices]
        fills = cross_row_consensus(family_records)
        for i in row_indices:
            mpn = df.at[i, "Mfg_Part_Num"]
            for label, cell in fills.get(mpn, {}).items():
                parsed_attrs_by_idx[i].setdefault(label, cell)

    # ---- Manufacturer / brand resolution ----
    records: list[EnrichedRecord] = []
    for idx, row in df.iterrows():
        classpath_name = classpath_by_idx.get(idx, "Unclassified")
        schema = get_classpath(classpath_name)
        attrs = dict(parsed_attrs_by_idx.get(idx, {}))

        # ---- Stage 3b: RAG retrieval for anything still missing (only fires if a corpus exists) ----
        missing = [a.label for a in schema.attributes if a.label not in attrs]
        if missing:
            retrieved = retrieval_enrich(row["Part_Desc"], row["Part_Manuf"], missing)
            for label, cell in retrieved.items():
                attrs[label] = cell

        # fill any attribute the schema declares but nothing produced a value for
        for attr_def in schema.attributes:
            attrs.setdefault(attr_def.label, Cell(state=ProvenanceState.BLANK_FLAGGED,
                                                    reason="no PARSED, INFERRED, or RETRIEVED value found"))

        # ---- Stage 4: validation ----
        for label in list(attrs.keys()):
            attrs[label] = validate.validate_vocabulary(attrs[label], schema, label)
            attrs[label] = validate.apply_structural_formatting(attrs[label], label)
        contradictions = validate.check_contradictions(attrs)

        manufacturer_cell, brand_cell = resolve_manufacturer_and_brand(
            row["Part_Desc"], row["Part_Manuf"], row["E1_Brand"], row["DIB_Brand"]
        )

        record = EnrichedRecord(
            row_index=idx,
            mfg_part_num=row["Mfg_Part_Num"],
            part_desc=row["Part_Desc"],
            part_manuf=row["Part_Manuf"],
            e1_brand=row["E1_Brand"],
            unilog_brand=row["Unilog_Brand"],
            dib_brand=row["DIB_Brand"],
            classpath=classpath_name,
            classification_confidence=confidence_by_idx.get(idx, 0.0),
            attributes=attrs,
            manufacturer_name=manufacturer_cell,
            brand_name=brand_cell,
        )
        records.append(record)

    # ---- statistical outlier pass (needs full family view, so runs after per-row loop) ----
    for family_key, row_indices in families.items():
        by_label: dict[str, list[Cell]] = defaultdict(list)
        for i in row_indices:
            rec = records[i]
            for label, cell in rec.attributes.items():
                by_label[label].append(cell)
        validate.flag_statistical_outliers(by_label)

    # ---- Stage 5: deterministic composition ----
    for record in records:
        schema = get_classpath(record.classpath)
        record.mobile_desc = compose.compose_mobile_desc(
            record.manufacturer_name, record.brand_name, schema.item_type, record.mfg_part_num,
            record.attributes, schema,
        )
        record.short_desc = compose.compose_short_desc(
            record.brand_name, schema.item_type, record.mfg_part_num, record.attributes, schema,
        )
        record.long_desc1 = compose.compose_long_desc1(
            record.brand_name, schema.item_type, record.attributes, schema,
        )
        record.retail_desc = compose.compose_retail_desc(
            schema.item_type, record.attributes, schema,
        )
        record.invoice_desc = compose.compose_invoice_desc(
            schema.item_type, record.attributes, schema,
        )
        record.recompute_flags()

    # ---- Stage 6: calibration ----
    for record in records:
        apply_calibration(record)

    stats["runtime_seconds"] = round(time.time() - t0, 2)
    stats["flagged_rows"] = sum(1 for r in records if r.flagged)
    stats["classpath_counts"] = dict(pd.Series([r.classpath for r in records]).value_counts())

    return records, stats
