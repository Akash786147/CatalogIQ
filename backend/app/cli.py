"""
Headless entrypoint - this is what gets evaluated. No server, no frontend
required.

    python -m app.cli enrich --input data/raw/input_sample.csv \
                              --output data/output/enriched.csv

    python -m app.cli correct --scope-field Part_Manuf \
                               --scope-value "Black & Decker/dewlt (2585)" \
                               --target-field MANUFACTURER_NAME \
                               --new-value "Stanley Black & Decker, Inc."
"""
from __future__ import annotations

import json
from pathlib import Path

import typer

from app.config import get_settings
from app.io.readers import load_input_csv, load_output_header
from app.io.writers import write_output, write_provenance
from app.pipeline import stage7_corrections as corrections
from app.pipeline.report import build_run_report
from app.pipeline.run import enrich_dataframe

app = typer.Typer(add_completion=False)


@app.command()
def enrich(
    input: Path = typer.Option(..., "--input", help="Path to input CSV (Mfg_Part_Num, Part_Desc, ...)"),
    output: Path = typer.Option(..., "--output", help="Path to write the 252-column enriched CSV/XLSX"),
    provenance_output: Path | None = typer.Option(None, "--provenance-output", help="Path for the parallel provenance file"),
    delivery_format: Path | None = typer.Option(None, "--delivery-format", help="Header template CSV (defaults to data/raw/delivery_format.csv)"),
    apply_corrections: bool = typer.Option(True, "--apply-corrections/--no-apply-corrections", help="Apply saved reviewer correction rules"),
    report: Path | None = typer.Option(None, "--report", help="Path to write a JSON run report"),
):
    settings = get_settings()
    delivery_format = delivery_format or settings.delivery_format_csv
    provenance_output = provenance_output or output.with_name(output.stem + "_provenance.csv")

    typer.echo(f"Loading {input} ...")
    df = load_input_csv(input)
    header = load_output_header(delivery_format)

    typer.echo(f"Enriching {len(df)} rows ...")
    records, stats = enrich_dataframe(df)

    if apply_corrections:
        db_path = settings.output_dir / "corrections.db"
        rules = corrections.load_correction_rules(db_path)
        if rules:
            affected = corrections.apply_correction_rules(records, rules)
            for summary, count in affected.items():
                typer.echo(f"  correction applied: {summary} -> {count} rows")

    raw_rows = df.to_dict("records")
    write_output(records, raw_rows, header, output)
    write_provenance(records, header, provenance_output)
    typer.echo(f"Wrote {output}")
    typer.echo(f"Wrote {provenance_output}")

    run_report = build_run_report(records, stats)
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(run_report, indent=2, default=str))
        typer.echo(f"Wrote {report}")
    else:
        typer.echo(json.dumps(run_report, indent=2, default=str))


@app.command()
def correct(
    scope_field: str = typer.Option(..., help="e.g. Part_Manuf"),
    scope_value: str = typer.Option(..., help="e.g. 'Black & Decker/dewlt (2585)'"),
    target_field: str = typer.Option(..., help="MANUFACTURER_NAME or BRAND_NAME"),
    new_value: str = typer.Option(...),
):
    """Save a reviewer correction rule. It's applied on the next `enrich` run."""
    settings = get_settings()
    db_path = settings.output_dir / "corrections.db"
    rule_id = corrections.add_correction_rule(db_path, scope_field, scope_value, target_field, new_value)
    typer.echo(f"Saved correction rule #{rule_id}. It will apply on the next `enrich` run.")


@app.command()
def list_corrections():
    settings = get_settings()
    db_path = settings.output_dir / "corrections.db"
    for rule in corrections.load_correction_rules(db_path):
        typer.echo(json.dumps(rule))


if __name__ == "__main__":
    app()
