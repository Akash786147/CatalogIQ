/** Mirrors backend/app/core/cell.py. Keep the two in sync. */

export type Provenance = "PARSED" | "LOOKUP" | "INFERRED" | "RETRIEVED";

export interface Evidence {
  source: string;
  /** Character offsets into Part_Desc, for PARSED values. */
  span?: [number, number] | null;
  /** Which sibling SKUs voted, for INFERRED values. */
  contributing_skus?: string[];
  /** Manufacturer document URL, for RETRIEVED values. */
  url?: string | null;
  snippet?: string | null;
}

export interface Cell {
  value: string | null;
  uom?: string | null;
  /** null means an honest gap — nothing supported a value. */
  state: Provenance | null;
  confidence: number;
  evidence?: Evidence | null;
  reason?: string | null;
}

export interface Attribute {
  label: string;
  cell: Cell;
}

export interface EnrichedRow {
  row_id: string;
  /** The six input columns, verbatim. */
  source: Record<string, string>;
  classpath: Cell;
  /** Flat 252-column values keyed by their exact output header. */
  fields: Record<string, Cell>;
  attributes: Attribute[];
  flags: string[];
}

export interface RunStats {
  run_id: string;
  input_file: string;
  completed_at: string;
  rows_total: number;
  rows_clean: number;
  rows_needing_review: number;
  cells_total: number;
  cells_populated: number;
  provenance_counts: Record<Provenance | "GAP", number>;
  /** 10 buckets, 0.0–1.0, of populated-cell confidence. */
  confidence_histogram: number[];
  lov_conformance: number;
  char_limit_compliance: number;
  cost_usd: number;
  llm_calls: number;
  analyst_hours_saved: number;
}

export interface CorrectionRule {
  id: string;
  scope_field: string;
  scope_value: string;
  field: string;
  value: string;
  author: string;
  created_at: string;
  rows_affected: number;
  rows_needing_rereview: number;
}

/** What POST /api/corrections returns — the "applied to 55 rows" moment. */
export interface PropagationResult {
  rule: CorrectionRule;
  rows_affected: number;
  rows_needing_rereview: number;
  sample_row_ids: string[];
}

export interface SearchHit {
  row_id: string;
  title: string;
  manufacturer: string;
  matched_on: string[];
}

export interface SearchComparison {
  query: string;
  raw: SearchHit[];
  enriched: SearchHit[];
}

export interface ReviewQueueParams {
  search?: string;
  manufacturer?: string;
  flag?: string;
  maxConfidence?: number;
}
