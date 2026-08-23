import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ConfidenceMeter, ProvenanceChip } from "@/components/Provenance";
import type { EnrichedRow } from "@/lib/types";

const FLAG_LABEL: Record<string, string> = {
  distributor_in_manufacturer_field: "Distributor in manufacturer field",
  manufacturer_resolution_uncertain: "Manufacturer uncertain",
  conflicts_with_ground_truth: "Conflicts with ground truth",
  low_confidence_attribute: "Low-confidence attribute",
};

const CRITICAL_FLAGS = new Set(["distributor_in_manufacturer_field", "conflicts_with_ground_truth"]);

/** Lowest confidence among populated attributes — what decides queue order. */
function weakest(row: EnrichedRow): number {
  const scores = row.attributes.filter((a) => a.cell.value).map((a) => a.cell.confidence);
  return scores.length ? Math.min(...scores) : 1;
}

function countGaps(row: EnrichedRow): number {
  return row.attributes.filter((a) => !a.cell.value).length;
}

export default function ReviewQueue() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [manufacturer, setManufacturer] = useState("");
  const [flag, setFlag] = useState("");

  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["rows", search, manufacturer, flag],
    queryFn: () => api.getRows({ search, manufacturer, flag }),
  });

  const { data: allRows = [] } = useQuery({ queryKey: ["rows", "", "", ""], queryFn: () => api.getRows({}) });

  const manufacturers = useMemo(
    () => [...new Set(allRows.map((r) => r.source.Part_Manuf))].sort(),
    [allRows],
  );
  const flags = useMemo(() => [...new Set(allRows.flatMap((r) => r.flags))].sort(), [allRows]);

  // Most-doubtful first: flagged rows rise, then lowest confidence.
  const sorted = useMemo(
    () =>
      [...rows].sort((a, b) => b.flags.length - a.flags.length || weakest(a) - weakest(b)),
    [rows],
  );

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Review queue</h1>
          <p>
            Ranked by doubt, not by row number. Open a product to see what every value was based
            on — and correct it once to fix it everywhere.
          </p>
        </div>
      </div>

      <div className="filters">
        <input
          className="input"
          style={{ minWidth: 260 }}
          placeholder="Search part number or description…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select className="select" value={manufacturer} onChange={(e) => setManufacturer(e.target.value)}>
          <option value="">All distributors</option>
          {manufacturers.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
        <select className="select" value={flag} onChange={(e) => setFlag(e.target.value)}>
          <option value="">All flags</option>
          {flags.map((f) => (
            <option key={f} value={f}>
              {FLAG_LABEL[f] ?? f}
            </option>
          ))}
        </select>
        {(search || manufacturer || flag) && (
          <button
            className="btn btn--ghost"
            onClick={() => {
              setSearch("");
              setManufacturer("");
              setFlag("");
            }}
          >
            Clear
          </button>
        )}
        <span className="tiny muted" style={{ marginLeft: "auto" }}>
          {sorted.length} product{sorted.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="table-wrap">
        <table className="rows">
          <thead>
            <tr>
              <th>Part number</th>
              <th>Input description</th>
              <th>Resolved brand</th>
              <th>Classpath</th>
              <th>Weakest value</th>
              <th>Gaps</th>
              <th>Flags</th>
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i}>
                  <td colSpan={7}>
                    <div className="skeleton" />
                  </td>
                </tr>
              ))}

            {!isLoading &&
              sorted.map((row) => {
                const brand = row.fields.BRAND_NAME;
                return (
                  <tr
                    key={row.row_id}
                    onClick={() => navigate(`/review/${encodeURIComponent(row.row_id)}`)}
                  >
                    <td>
                      <span className="mono" style={{ fontWeight: 600 }}>
                        {row.row_id}
                      </span>
                      <div className="tiny muted" style={{ marginTop: 2 }}>
                        {row.source.Part_Manuf}
                      </div>
                    </td>
                    <td style={{ maxWidth: 300 }} className="mono tiny">
                      {row.source.Part_Desc}
                    </td>
                    <td>
                      {brand?.value ? (
                        <>
                          <div style={{ fontWeight: 600 }}>{brand.value}</div>
                          <div style={{ marginTop: 3 }}>
                            <ProvenanceChip state={brand.state} />
                          </div>
                        </>
                      ) : (
                        <span className="muted tiny">—</span>
                      )}
                    </td>
                    <td style={{ maxWidth: 220 }} className="tiny">
                      {row.classpath.value ?? <span className="muted">unclassified</span>}
                    </td>
                    <td>
                      <ConfidenceMeter value={weakest(row)} />
                    </td>
                    <td className="tiny muted">{countGaps(row)} blank</td>
                    <td>
                      {row.flags.length === 0 ? (
                        <span className="tiny" style={{ color: "var(--good)", fontWeight: 700 }}>
                          ✓ clean
                        </span>
                      ) : (
                        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                          {row.flags.map((f) => (
                            <span
                              key={f}
                              className={`flagchip${CRITICAL_FLAGS.has(f) ? " flagchip--critical" : ""}`}
                            >
                              {FLAG_LABEL[f] ?? f}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}

            {!isLoading && sorted.length === 0 && (
              <tr>
                <td colSpan={7}>
                  <div className="empty">
                    <div className="empty__title">Nothing matches those filters</div>
                    <div>Clear them to see the full queue.</div>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
