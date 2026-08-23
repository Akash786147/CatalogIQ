import type { Cell, Provenance } from "@/lib/types";

/** Human-facing wording. "GAP" is deliberately phrased as a decision, not a
 *  failure — the product's whole claim is that a blank is trustworthy. */
export const PROVENANCE_LABEL: Record<Provenance | "GAP", string> = {
  PARSED: "Parsed",
  LOOKUP: "Lookup",
  INFERRED: "Inferred",
  RETRIEVED: "Retrieved",
  GAP: "Left blank",
};

export const PROVENANCE_BLURB: Record<Provenance | "GAP", string> = {
  PARSED: "Read directly out of the input text, with the exact characters recorded",
  LOOKUP: "Matched against an approved controlled vocabulary",
  INFERRED: "Agreed on by sibling products in the same family",
  RETRIEVED: "Taken from the manufacturer's own documentation",
  GAP: "No evidence supported a value, so none was written",
};

/** Palette validated in both modes — see src/styles/theme.css. */
export const PROVENANCE_VAR: Record<Provenance | "GAP", string> = {
  PARSED: "var(--prov-parsed)",
  LOOKUP: "var(--prov-lookup)",
  INFERRED: "var(--prov-inferred)",
  RETRIEVED: "var(--prov-retrieved)",
  GAP: "var(--prov-gap)",
};

export const PROVENANCE_ORDER: (Provenance | "GAP")[] = [
  "PARSED",
  "LOOKUP",
  "INFERRED",
  "RETRIEVED",
  "GAP",
];

export function ProvenanceChip({ state }: { state: Provenance | null }) {
  const key = state ?? "GAP";
  return (
    <span className={`chip chip--${key}`} title={PROVENANCE_BLURB[key]}>
      <span className="chip__dot" aria-hidden />
      {PROVENANCE_LABEL[key]}
    </span>
  );
}

/** Confidence as a bar plus the number. Never color-alone: the digits carry it. */
export function ConfidenceMeter({ value, threshold = 0.85 }: { value: number; threshold?: number }) {
  const pct = Math.round(value * 100);
  const color = value >= threshold ? "var(--good)" : value >= 0.6 ? "var(--warning)" : "var(--critical)";
  return (
    <span className="conf" title={`${pct}% confidence`}>
      <span className="conf__track">
        <span className="conf__fill" style={{ width: `${pct}%`, background: color }} />
      </span>
      <span className="conf__num" style={{ color }}>
        {pct}%
      </span>
    </span>
  );
}

/** Renders Part_Desc with the character span of a PARSED value highlighted.
 *  This is what turns "trust me" into "look — those characters, right there." */
export function EvidenceSource({ text, span }: { text: string; span?: [number, number] | null }) {
  if (!span) return <div className="evidence-source">{text}</div>;
  const [start, end] = span;
  return (
    <div className="evidence-source">
      {text.slice(0, start)}
      <mark>{text.slice(start, end)}</mark>
      {text.slice(end)}
    </div>
  );
}

export function cellDisplay(cell: Cell): string {
  if (!cell.value) return "";
  return cell.uom ? `${cell.value} ${cell.uom}` : cell.value;
}
