/** The single seam between the UI and the pipeline.
 *
 * Every component talks to this module and nothing else. It calls the FastAPI
 * backend directly — there is no mock layer.
 *
 * In development, vite.config.ts proxies /api to http://localhost:8000, so
 * VITE_API_BASE can stay empty and no CORS setup is needed. Set VITE_API_BASE
 * only when the backend lives on a different origin.
 *
 * Backend contract — backend/app/api/routes.py:
 *   GET  /api/runs/latest                  -> RunStats
 *   POST /api/runs                         -> re-run the pipeline
 *   GET  /api/rows?search=&manufacturer=   -> EnrichedRow[]
 *   GET  /api/rows/:rowId                  -> EnrichedRow
 *   POST /api/corrections                  -> PropagationResult
 *   GET  /api/search?q=                    -> SearchComparison
 *   GET  /api/manufacturers                -> string[]
 *   GET  /api/flags                        -> string[]
 */

import type {
  EnrichedRow,
  PropagationResult,
  ReviewQueueParams,
  RunStats,
  SearchComparison,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    // FastAPI puts the useful part in `detail`; surface it rather than a bare status.
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* non-JSON error body — the status line is all we have */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getRunStats(): Promise<RunStats> {
    return request<RunStats>("/api/runs/latest");
  },

  /** Re-runs the pipeline over the configured input CSV. */
  rerun(): Promise<{ status: string; rows: number; runtime_seconds: number }> {
    return request("/api/runs", { method: "POST" });
  },

  getRows(params: ReviewQueueParams = {}): Promise<EnrichedRow[]> {
    const qs = new URLSearchParams();
    if (params.search) qs.set("search", params.search);
    if (params.manufacturer) qs.set("manufacturer", params.manufacturer);
    if (params.flag) qs.set("flag", params.flag);
    if (params.maxConfidence != null) qs.set("max_confidence", String(params.maxConfidence));
    return request<EnrichedRow[]>(`/api/rows?${qs}`);
  },

  getRow(rowId: string): Promise<EnrichedRow> {
    return request<EnrichedRow>(`/api/rows/${encodeURIComponent(rowId)}`);
  },

  /** The demo moment: one correction becomes a rule, and the rule reports its
   *  blast radius across the batch. */
  submitCorrection(input: {
    rowId: string;
    field: string;
    value: string;
    scopeField: string;
    scopeValue: string;
  }): Promise<PropagationResult> {
    return request<PropagationResult>("/api/corrections", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  compareSearch(query: string): Promise<SearchComparison> {
    return request<SearchComparison>(`/api/search?q=${encodeURIComponent(query)}`);
  },

  getManufacturers(): Promise<string[]> {
    return request<string[]>("/api/manufacturers");
  },

  getFlags(): Promise<string[]> {
    return request<string[]>("/api/flags");
  },
};
