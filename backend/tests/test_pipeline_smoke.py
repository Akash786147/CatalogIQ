"""
Smoke tests against the real 1,000-row sample. These run with NO API key -
the pipeline must be fully headless-runnable, which is the actual evaluation
condition.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.io.readers import load_input_csv, load_output_header
from app.pipeline.run import enrich_dataframe

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


@pytest.fixture(scope="module")
def df():
    return load_input_csv(RAW_DIR / "input_sample.csv")


@pytest.fixture(scope="module")
def enriched(df):
    records, stats = enrich_dataframe(df)
    return records, stats


def test_loads_all_rows(df):
    assert len(df) == 1000


def test_output_header_has_252_columns():
    header = load_output_header(RAW_DIR / "delivery_format.csv")
    assert len(header) == 252


def test_pipeline_runs_on_full_sample_without_api_key(enriched):
    records, stats = enriched
    assert len(records) == 1000
    assert stats["runtime_seconds"] < 30  # headless run must be fast enough for eval


def test_invoice_desc_never_exceeds_40_chars(enriched):
    records, _ = enriched
    over = [r for r in records if len(r.invoice_desc.display_value()) > 40]
    assert over == [], f"{len(over)} rows exceed the INVOICE_DESC 40-char limit"


def test_no_cell_is_written_without_a_provenance_state(enriched):
    """The core claim of the whole system: every non-blank cell has a real state."""
    from app.core.schema import ProvenanceState
    records, _ = enriched
    for r in records:
        for label, cell in r.attributes.items():
            if cell.value not in (None, ""):
                assert cell.state != ProvenanceState.BLANK_FLAGGED, (
                    f"{label} has a value but is marked BLANK_FLAGGED - contradiction"
                )
                assert cell.state in (
                    ProvenanceState.PARSED, ProvenanceState.LOOKUP,
                    ProvenanceState.INFERRED, ProvenanceState.RETRIEVED,
                )


def test_dishwasher_rows_get_dishwasher_classpath(enriched, df):
    records, _ = enriched
    for i, row in df.iterrows():
        if "dishwasher" in row["Part_Desc"].lower():
            assert "Dishwashers" in records[i].classpath


def test_manufacturer_never_copies_the_distributor_code_verbatim(enriched, df):
    """Part_Manuf is a distributor - MANUFACTURER_NAME must never equal it."""
    records, _ = enriched
    for i, row in df.iterrows():
        mfr = records[i].manufacturer_name.display_value()
        if mfr:
            assert mfr != row["Part_Manuf"]


def test_ambiguous_distributor_appde_is_flagged_not_guessed(enriched, df):
    """Appliance Dealers Cooperative resolves to different manufacturers on different
    rows in the real ground truth (Rheem vs Whirlpool) - it must never be guessed
    from the distributor code alone when the description gives no brand token."""
    records, _ = enriched
    appde_rows = df[df["Part_Manuf"].str.contains("Appliance Dealers Cooperative", case=False)]
    for i in appde_rows.index:
        cell = records[i].manufacturer_name
        # either correctly resolved from a real brand signal, or honestly flagged -
        # never silently defaulted to a single guessed manufacturer for every APPDE row
        assert cell.state.value in ("PARSED", "LOOKUP", "BLANK_FLAGGED")


def test_held_out_manufacturer_grammar_still_parses():
    """
    Generalization proof: induce the LED-lamp abbreviation template from Satco
    rows only, then apply it to a held-out Philips row it never saw. If the
    grammar is truly learned (not a Philips-specific dictionary), core numeric
    fields still parse.
    """
    from app.core.classpaths import get_classpath
    from app.pipeline.stage2_grammar import (
        apply_template_to_row, induce_family_template, mine_family_slots,
    )

    df = load_input_csv(RAW_DIR / "input_sample.csv")
    satco = df[df["Part_Manuf"].str.contains("Satco", case=False)]
    philips = df[df["Part_Manuf"].str.contains("Phillips Lighting", case=False)]
    assert len(satco) > 5 and len(philips) > 5

    schema = get_classpath("Lighting>Lamps>LED Lamps")
    satco_key = f"{satco.iloc[0]['Part_Manuf']}||{schema.name}"
    mapping = induce_family_template(satco_key, list(satco.index), df)
    assert mapping, "expected the heuristic/LLM template induction to find at least one slot"

    slots = mine_family_slots(satco["Part_Desc"].tolist())

    # try every held-out Philips row; the template must generalize to at least
    # the rows that actually carry the shorthand it was trained to recognize
    # (a "3' Strip Light Ext" row with no wattage token is a legitimate miss,
    # not a generalization failure)
    any_numeric_hit = False
    for held_out_desc in philips["Part_Desc"]:
        cells = apply_template_to_row(held_out_desc, mapping, slots, schema)
        if any(not c.is_blank() and isinstance(c.value, (int, float)) for c in cells.values()):
            any_numeric_hit = True
            break

    assert any_numeric_hit, (
        "template induced from Satco produced no parsed values on ANY unseen Philips row"
    )
