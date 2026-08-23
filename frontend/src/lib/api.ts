/** The single seam between the UI and the pipeline.
 *
 * Every component talks to this module and nothing else. While the backend is
 * being built, `USE_MOCK` serves fixtures shaped exactly like the real
 * responses. To go live: set `VITE_USE_MOCK=false` (or just start the backend
 * — see below). No component changes.
 *
 * Backend contract, matching backend/app/api/routes/:
 *   GET  /api/runs/latest                  -> RunStats
 *   GET  /api/rows?search=&manufacturer=   -> EnrichedRow[]
 *   GET  /api/rows/:rowId                  -> EnrichedRow
 *   POST /api/corrections                  -> PropagationResult
 *   GET  /api/search?q=                    -> SearchComparison
 */

import type {
  EnrichedRow,
  PropagationResult,
  ReviewQueueParams,
  RunStats,
  SearchComparison,
} from "./types";
import * as mock from "./mockData";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

/** Defaults to mock unless explicitly disabled, so `npm run dev` works alone. */
export const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

/** Small delay on mock reads so loading states are actually exercised. */
const settle = <T>(value: T, ms = 220): Promise<T> =>
  new Promise((resolve) => setTimeout(() => resolve(value), ms));

export const api = {
  getRunStats(): Promise<RunStats> {
    return USE_MOCK ? settle(mock.runStats) : request<RunStats>("/api/runs/latest");
  },

  getRows(params: ReviewQueueParams = {}): Promise<EnrichedRow[]> {
    if (USE_MOCK) return settle(mock.filterRows(params));
    const qs = new URLSearchParams();
    if (params.search) qs.set("search", params.search);
    if (params.manufacturer) qs.set("manufacturer", params.manufacturer);
    if (params.flag) qs.set("flag", params.flag);
    if (params.maxConfidence != null) qs.set("max_confidence", String(params.maxConfidence));
    return request<EnrichedRow[]>(`/api/rows?${qs}`);
  },

  getRow(rowId: string): Promise<EnrichedRow> {
    if (USE_MOCK) {
      const row = mock.rows.find((r) => r.row_id === rowId);
      if (!row) return Promise.reject(new Error(`No row ${rowId}`));
      return settle(row);
    }
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
    if (USE_MOCK) return settle(mock.propagate(input), 500);
    return request<PropagationResult>("/api/corrections", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  compareSearch(query: string): Promise<SearchComparison> {
    if (USE_MOCK) return settle(mock.compareSearch(query), 320);
    return request<SearchComparison>(`/api/search?q=${encodeURIComponent(query)}`);
  },
};
