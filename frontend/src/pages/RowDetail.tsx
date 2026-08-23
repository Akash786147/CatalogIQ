import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import {
  ConfidenceMeter,
  EvidenceSource,
  PROVENANCE_BLURB,
  ProvenanceChip,
  cellDisplay,
} from "@/components/Provenance";
import type { Cell, PropagationResult } from "@/lib/types";

/** The fields a reviewer actually adjudicates, in the order they matter. */
const KEY_FIELDS = [
  "MANUFACTURER_NAME",
  "BRAND_NAME",
  "MANUFACTURER_PART_NUMBER",
  "Product Name",
  "MOBILE_DESC",
  "INVOICE_DESC",
];

function FieldRow({
  label,
  cell,
  onSelect,
  selected,
  onCorrect,
}: {
  label: string;
  cell: Cell;
  onSelect?: () => void;
  selected?: boolean;
  onCorrect?: () => void;
}) {
  const populated = Boolean(cell.value);
  return (
    <div
      className={`fieldrow${selected ? " fieldrow--selected" : ""}`}
      onMouseEnter={onSelect}
      style={{ cursor: cell.evidence?.span ? "pointer" : undefined }}
    >
      <div className="fieldrow__label">{label}</div>
      <div className={populated ? "fieldrow__value" : "fieldrow__value fieldrow__value--gap"}>
        {populated ? (
          <>
            {cell.value}
            {cell.uom ? <span className="uom">{cell.uom}</span> : null}
          </>
        ) : (
          (cell.reason ?? "Left blank — no evidence supported a value")
        )}
        {cell.reason && populated ? <div className="fieldrow__reason">{cell.reason}</div> : null}
        {cell.evidence?.url ? (
          <div className="fieldrow__reason">
            <a href={cell.evidence.url} target="_blank" rel="noreferrer">
              ↗ manufacturer source
            </a>
            {cell.evidence.snippet ? <> — “{cell.evidence.snippet}”</> : null}
          </div>
        ) : null}
        {cell.evidence?.contributing_skus?.length ? (
          <div className="fieldrow__reason">
            Agreed by{" "}
            <span className="mono">{cell.evidence.contributing_skus.join(", ")}</span>
          </div>
        ) : null}
      </div>
      <div className="fieldrow__meta">
        {populated ? <ConfidenceMeter value={cell.confidence} /> : null}
        <ProvenanceChip state={cell.state} />
        {onCorrect ? (
          <button className="btn btn--ghost btn--sm" onClick={onCorrect}>
            Correct
          </button>
        ) : null}
      </div>
    </div>
  );
}

export default function RowDetail() {
  const { rowId = "" } = useParams();
  const queryClient = useQueryClient();
  const [activeSpan, setActiveSpan] = useState<[number, number] | null>(null);
  const [activeLabel, setActiveLabel] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [result, setResult] = useState<PropagationResult | null>(null);

  const { data: row, isLoading } = useQuery({
    queryKey: ["row", rowId],
    queryFn: () => api.getRow(rowId),
  });

  const correction = useMutation({
    mutationFn: api.submitCorrection,
    onSuccess: (res) => {
      setResult(res);
      setEditing(null);
      queryClient.invalidateQueries({ queryKey: ["rows"] });
    },
  });

  if (isLoading || !row) {
    return <div className="skeleton" style={{ height: 200 }} />;
  }

  const startEdit = (field: string, current: string) => {
    setEditing(field);
    setDraft(current);
    setResult(null);
  };

  const composed = ["MOBILE_DESC", "INVOICE_DESC"].filter((f) => row.fields[f]?.value);

  return (
    <>
      <div className="page-head">
        <div>
          <Link to="/review" className="tiny">
            ← Back to queue
          </Link>
          <h1 style={{ marginTop: 10 }}>
            <span className="mono">{row.row_id}</span>
          </h1>
          <p>
            {row.classpath.value ?? "Unclassified"} · supplied by {row.source.Part_Manuf}
          </p>
        </div>
        <div className="tiny muted">
          {row.attributes.filter((a) => a.cell.value).length} of {row.attributes.length} attributes
          evidenced
        </div>
      </div>

      {result ? (
        <div className="banner banner--good">
          <span className="banner__icon">
            <span aria-hidden>✓</span>
          </span>
          <div className="banner__body">
            <strong>
              Correction saved as a rule — applied to {result.rows_affected} rows.
            </strong>{" "}
            {result.rows_needing_rereview} rows have downstream descriptions that were rebuilt and
            now need a quick re-check. The fix was stored as{" "}
            <span className="mono">
              {result.rule.scope_field} = “{result.rule.scope_value}”
            </span>
            , not as a patch to this one cell — so the same mistake cannot recur across the batch.
          </div>
        </div>
      ) : null}

      {row.flags.length > 0 && !result ? (
        <div className="banner banner--warn">
          <span className="banner__icon">
            <span aria-hidden>!</span>
          </span>
          <div className="banner__body">
            <strong>This product was flagged.</strong>{" "}
            {row.flags.includes("distributor_in_manufacturer_field")
              ? "Part_Manuf is a distributor, not a manufacturer — the value below was copied through and needs resolving."
              : "One or more values fell below the auto-approval threshold."}
          </div>
        </div>
      ) : null}

      <div className="detail-grid">
        <div style={{ display: "grid", gap: 18 }}>
          <section className="card">
            <div className="card__head">
              <div className="card__title">Resolved identity</div>
              <div className="card__hint">
                Hover a value to see exactly which characters of the input justified it
              </div>
            </div>
            <div className="card__body" style={{ paddingTop: 4 }}>
              {KEY_FIELDS.filter((f) => row.fields[f]).map((field) => {
                const cell = row.fields[field];
                return (
                  <div key={field}>
                    <FieldRow
                      label={field}
                      cell={cell}
                      selected={activeLabel === field}
                      onSelect={() => {
                        setActiveLabel(field);
                        setActiveSpan(cell.evidence?.span ?? null);
                      }}
                      onCorrect={() => startEdit(field, cell.value ?? "")}
                    />
                    {editing === field ? (
                      <div
                        style={{
                          display: "flex",
                          gap: 8,
                          padding: "10px 0 14px",
                          alignItems: "center",
                          flexWrap: "wrap",
                        }}
                      >
                        <input
                          className="input"
                          style={{ flex: 1, minWidth: 240 }}
                          value={draft}
                          autoFocus
                          onChange={(e) => setDraft(e.target.value)}
                          placeholder={`Correct value for ${field}`}
                        />
                        <button
                          className="btn btn--accent"
                          disabled={!draft.trim() || correction.isPending}
                          onClick={() =>
                            correction.mutate({
                              rowId: row.row_id,
                              field,
                              value: draft.trim(),
                              scopeField: "Part_Manuf",
                              scopeValue: row.source.Part_Manuf,
                            })
                          }
                        >
                          {correction.isPending ? "Applying…" : "Apply to every matching row"}
                        </button>
                        <button className="btn btn--ghost" onClick={() => setEditing(null)}>
                          Cancel
                        </button>
                        <div className="tiny muted" style={{ flexBasis: "100%" }}>
                          Saved as a rule scoped to{" "}
                          <span className="mono">Part_Manuf = “{row.source.Part_Manuf}”</span>, so
                          every product from this distributor is fixed at once.
                        </div>
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </section>

          <section className="card">
            <div className="card__head">
              <div className="card__title">
                Attributes ({row.attributes.filter((a) => a.cell.value).length} of{" "}
                {row.attributes.length} filled)
              </div>
              <div className="card__hint">
                The label list comes from the category schema. Blanks are gaps we chose not to
                guess at.
              </div>
            </div>
            <div className="card__body" style={{ paddingTop: 4 }}>
              {row.attributes.map((attr) => (
                <FieldRow
                  key={attr.label}
                  label={attr.label}
                  cell={attr.cell}
                  selected={activeLabel === attr.label}
                  onSelect={() => {
                    setActiveLabel(attr.label);
                    setActiveSpan(attr.cell.evidence?.span ?? null);
                  }}
                />
              ))}
            </div>
          </section>
        </div>

        <aside style={{ display: "grid", gap: 18, position: "sticky", top: 78 }}>
          <section className="card">
            <div className="card__head">
              <div className="card__title">The input we were given</div>
              <div className="card__hint">Six columns. This is all the evaluator hands us.</div>
            </div>
            <div className="card__body">
              <EvidenceSource text={row.source.Part_Desc} span={activeSpan} />
              <div style={{ marginTop: 14, display: "grid", gap: 9 }}>
                {Object.entries(row.source)
                  .filter(([k]) => k !== "Part_Desc")
                  .map(([k, v]) => {
                    // The backend scrubs "-- Unbranded --" and friends to "" on
                    // ingest, so an empty string here means the column carried
                    // no signal. Say that, rather than rendering a blank row.
                    const empty = !v || v.startsWith("--");
                    return (
                      <div key={k} className="srcrow">
                        <span className="srcrow__key">{k}</span>
                        <span className={`srcrow__val${empty ? " srcrow__val--placeholder" : ""}`}>
                          {empty ? "— no value" : v}
                        </span>
                      </div>
                    );
                  })}
              </div>
            </div>
          </section>

          <section className="card">
            <div className="card__head">
              <div className="card__title">
                {activeLabel ? `Why: ${activeLabel}` : "Evidence tiers"}
              </div>
            </div>
            <div className="card__body" style={{ display: "grid", gap: 10 }}>
              {(["PARSED", "LOOKUP", "INFERRED", "RETRIEVED", "GAP"] as const).map((tier) => (
                <div key={tier} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                  <ProvenanceChip state={tier === "GAP" ? null : tier} />
                  <span className="tiny muted" style={{ flex: 1 }}>
                    {PROVENANCE_BLURB[tier]}
                  </span>
                </div>
              ))}
            </div>
          </section>

          {/* Only render once composition has actually run for this row —
              an empty card reads as a bug, not as an honest gap. */}
          {composed.length > 0 ? (
          <section className="card">
            <div className="card__head">
              <div className="card__title">Composed descriptions</div>
              <div className="card__hint">
                Built from the facts above by formula — never written by a model
              </div>
            </div>
            <div className="card__body" style={{ display: "grid", gap: 12 }}>
              {composed.map((f) => {
                const cell = row.fields[f];
                return (
                  <div key={f}>
                    <div className="tiny muted" style={{ fontWeight: 700 }}>
                      {f}
                      {f === "INVOICE_DESC" ? ` · ${(cell.value ?? "").length}/40 chars` : ""}
                    </div>
                    <div className="mono" style={{ marginTop: 3 }}>
                      {cellDisplay(cell)}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
          ) : null}
        </aside>
      </div>
    </>
  );
}
