import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { SearchComparison, SearchHit } from "@/lib/types";

const SUGGESTIONS = ["2700K medium base LED 40W", "5000K LED downlight 6 in", "20V grease gun"];

function Results({ hits, empty }: { hits: SearchHit[]; empty: string }) {
  if (hits.length === 0) {
    return (
      <div className="empty">
        <div className="empty__title">No results</div>
        <div className="tiny">{empty}</div>
      </div>
    );
  }
  return (
    <div>
      {hits.map((hit) => (
        <div className="hit" key={hit.row_id}>
          <div className="hit__title">{hit.title}</div>
          <div className="hit__meta">
            <span className="mono">{hit.row_id}</span> · {hit.manufacturer}
          </div>
          <div>
            {hit.matched_on.map((m) => (
              <span className="hit__match" key={m}>
                matched on {m}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function SearchProof() {
  const [query, setQuery] = useState(SUGGESTIONS[1]);
  const [comparison, setComparison] = useState<SearchComparison | null>(null);

  const run = useMutation({
    mutationFn: (q: string) => api.compareSearch(q),
    onSuccess: setComparison,
  });

  const submit = (q: string) => {
    setQuery(q);
    run.mutate(q);
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--dark">
            <span aria-hidden>❯</span> The commercial case
          </div>
          <h1>Search proof</h1>
          <p>
            The commercial case in one query. A buyer searches the way a buyer talks — the raw
            catalogue answers with nothing, because the facts are locked inside trade shorthand.
            The enriched catalogue answers correctly.
          </p>
        </div>
      </div>

      <form
        className="filters"
        onSubmit={(e) => {
          e.preventDefault();
          submit(query);
        }}
      >
        <input
          className="input"
          style={{ flex: 1, minWidth: 280 }}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search the catalogue as a buyer would…"
        />
        <button className="btn btn--primary" type="submit" disabled={run.isPending}>
          {run.isPending ? "Searching…" : "Run both searches"}
        </button>
      </form>

      <div className="filters" style={{ marginTop: -6 }}>
        <span className="tiny muted">Try:</span>
        {SUGGESTIONS.map((s) => (
          <button key={s} type="button" className="btn btn--sm" onClick={() => submit(s)}>
            {s}
          </button>
        ))}
      </div>

      {comparison ? (
        <div className="compare">
          <section className="card">
            <div className="card__head">
              <div className="card__title">Raw catalogue</div>
              <div className="card__hint">Searching the original Part_Desc column</div>
            </div>
            <div className="card__body">
              <Results
                hits={comparison.raw}
                empty={`"${comparison.query}" appears nowhere in the raw text — the catalogue stores it as shorthand like "10w LED 6\\" Retro 50k".`}
              />
            </div>
          </section>

          <section className="card">
            <div className="card__head">
              <div className="card__title">Enriched catalogue</div>
              <div className="card__hint">Searching the validated attribute layer</div>
            </div>
            <div className="card__body">
              <Results
                hits={comparison.enriched}
                empty="No product in the sample matches that query."
              />
            </div>
          </section>
        </div>
      ) : (
        <div className="card">
          <div className="card__body">
            <div className="empty">
              <div className="empty__title">Run a search to compare</div>
              <div className="tiny">
                Both sides query the same 1,000 products — only the content differs.
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
