import { useState } from "react";
import { PROVENANCE_BLURB, PROVENANCE_LABEL, PROVENANCE_ORDER, PROVENANCE_VAR } from "./Provenance";
import type { Provenance } from "@/lib/types";

const fmt = new Intl.NumberFormat("en-US");

/** Where every populated cell's value came from, as one 100% stacked bar.
 *
 * Categorical encoding: five fixed hues assigned in fixed order, never cycled.
 * The palette passed the CVD check with a low tritan margin, so identity is
 * carried by a legend AND direct value labels, never by color alone. Segments
 * are separated by a 2px surface gap.
 */
export function ProvenanceBar({ counts }: { counts: Record<Provenance | "GAP", number> }) {
  const [hover, setHover] = useState<string | null>(null);
  const total = PROVENANCE_ORDER.reduce((sum, k) => sum + (counts[k] ?? 0), 0);
  if (!total) return null;

  return (
    <div>
      <div
        style={{ display: "flex", gap: 2, height: 34, borderRadius: 6, overflow: "hidden" }}
        role="img"
        aria-label="Share of cells by evidence source"
      >
        {PROVENANCE_ORDER.map((key) => {
          const n = counts[key] ?? 0;
          if (!n) return null;
          const pct = (n / total) * 100;
          return (
            <div
              key={key}
              onMouseEnter={() => setHover(key)}
              onMouseLeave={() => setHover(null)}
              title={`${PROVENANCE_LABEL[key]} — ${fmt.format(n)} cells (${pct.toFixed(1)}%)`}
              style={{
                width: `${pct}%`,
                background: PROVENANCE_VAR[key],
                opacity: hover && hover !== key ? 0.45 : 1,
                transition: "opacity .15s",
                display: "grid",
                placeItems: "center",
                color: "#fff",
                fontSize: 11,
                fontWeight: 800,
                minWidth: 2,
              }}
            >
              {/* Direct label only where it actually fits — never on every segment. */}
              {pct > 8 ? `${pct.toFixed(0)}%` : ""}
            </div>
          );
        })}
      </div>

      <div className="legend">
        {PROVENANCE_ORDER.map((key) => {
          const n = counts[key] ?? 0;
          return (
            <span key={key} className="legend__item" title={PROVENANCE_BLURB[key]}>
              <span className="legend__swatch" style={{ background: PROVENANCE_VAR[key] }} />
              {PROVENANCE_LABEL[key]}
              <span className="legend__value">{fmt.format(n)}</span>
            </span>
          );
        })}
      </div>
    </div>
  );
}

/** Distribution of confidence across populated cells.
 *
 * One series, so no legend box — the title names it. Magnitude, so a single
 * hue. Bars carry 4px rounded tops anchored to the baseline, and the region
 * below the auto-approval threshold is tinted to show what lands in the queue.
 */
export function ConfidenceHistogram({
  buckets,
  threshold = 0.85,
}: {
  buckets: number[];
  threshold?: number;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(...buckets, 1);
  const H = 132;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: H }}>
        {buckets.map((n, i) => {
          const lo = i / buckets.length;
          const hi = (i + 1) / buckets.length;
          const belowThreshold = hi <= threshold;
          const h = Math.max((n / max) * H, n > 0 ? 3 : 0);
          return (
            <div
              key={i}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
              title={`${Math.round(lo * 100)}–${Math.round(hi * 100)}% confidence · ${fmt.format(n)} cells`}
              style={{
                flex: 1,
                height: h,
                borderRadius: "4px 4px 0 0",
                background: belowThreshold ? "var(--warning)" : "var(--prov-parsed)",
                opacity: hover !== null && hover !== i ? 0.5 : 1,
                transition: "opacity .15s",
                cursor: "default",
              }}
            />
          );
        })}
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: 7,
          fontSize: 11.5,
          color: "var(--ink-secondary)",
        }}
      >
        <span>0%</span>
        <span>
          {hover !== null
            ? `${fmt.format(buckets[hover])} cells at ${hover * 10}–${(hover + 1) * 10}%`
            : `auto-approve at ${Math.round(threshold * 100)}%+`}
        </span>
        <span>100%</span>
      </div>

      <div className="legend">
        <span className="legend__item">
          <span className="legend__swatch" style={{ background: "var(--warning)" }} />
          Goes to the review queue
        </span>
        <span className="legend__item">
          <span className="legend__swatch" style={{ background: "var(--prov-parsed)" }} />
          Auto-approved
        </span>
      </div>
    </div>
  );
}
