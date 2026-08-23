import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ConfidenceHistogram, ProvenanceBar } from "@/components/Charts";

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;
const num = new Intl.NumberFormat("en-US");

export default function Dashboard() {
  const { data, isLoading } = useQuery({ queryKey: ["run"], queryFn: api.getRunStats });

  // Polled only while the run is still building, so the warming state can say
  // what is actually happening rather than showing a bare skeleton for minutes.
  const { data: status } = useQuery({
    queryKey: ["status"],
    queryFn: api.getStatus,
    enabled: !data,
    refetchInterval: (q) => (q.state.data?.ready ? false : 4_000),
  });
  const warming = !data && status?.state !== "failed";

  if (isLoading || !data) {
    return (
      <>
        <div className="hero">
          <div className="eyebrow">
            <span aria-hidden>❯</span> {warming ? "Enriching" : "Loading"}
          </div>
          <h1>{warming ? "Running the pipeline…" : "Loading run…"}</h1>
          {warming ? (
            <p>
              The first request builds the whole run: 1,000 rows through seven stages
              {status?.llm_provider ? ` with ${status.llm_provider} classification` : ""}. This
              takes under a minute on a warm instance, longer on a cold one. The page fills in on
              its own — no need to refresh.
            </p>
          ) : null}
        </div>
        <div className="tiles">
          {Array.from({ length: 4 }).map((_, i) => (
            <div className="tile" key={i}>
              <div className="skeleton" style={{ width: "55%" }} />
              <div className="skeleton" style={{ height: 30, width: "42%", marginTop: 12 }} />
            </div>
          ))}
        </div>
      </>
    );
  }

  const fillRate = data.cells_populated / data.cells_total;
  const autoApproved = data.rows_clean / data.rows_total;

  return (
    <>
      <section className="hero">
        <div className="eyebrow">
          <span aria-hidden>❯</span> Evidence-first product content
        </div>
        <div className="hero__row">
          <div>
            <h1>
              {num.format(data.rows_clean)} products ready.
              <br />
              {data.rows_needing_review} need a human.
            </h1>
            <p>
              Enriched from <span className="mono">{data.input_file}</span> — six columns of
              distributor shorthand into the full 252-column delivery format. Every populated cell
              below can be traced to its source, and nothing was invented to fill a blank.
            </p>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <Link to="/review" className="btn btn--accent">
              Open the review queue
            </Link>
            <Link to="/search" className="btn btn--ghost-light">
              See the search proof
            </Link>
          </div>
        </div>
      </section>

      <div className="tiles">
        <div className="tile tile--good">
          <div className="tile__label">Auto-approved</div>
          <div className="tile__value">{num.format(data.rows_clean)}</div>
          <div className="tile__foot">{pct(autoApproved)} of rows need no human review</div>
        </div>
        <div className="tile tile--gold">
          <div className="tile__label">Needs a human</div>
          <div className="tile__value">{num.format(data.rows_needing_review)}</div>
          <div className="tile__foot">Flagged, ranked by doubt, and queued</div>
        </div>
        <div className="tile tile--navy">
          <div className="tile__label">Analyst-hours avoided</div>
          <div className="tile__value">{num.format(data.analyst_hours_saved)}</div>
          <div className="tile__foot">
            On the {num.format(data.rows_clean)} auto-approved rows only, at ~15 SKUs per analyst
            per day. Reviewing the other {data.rows_needing_review} still costs time.
          </div>
        </div>
        <div className="tile tile--blue">
          <div className="tile__label">Run time</div>
          <div className="tile__value">{data.runtime_seconds.toFixed(1)}s</div>
          <div className="tile__foot">
            {data.llm_calls === 0
              ? "0 model calls — every value came from a deterministic path"
              : `${data.llm_calls} ${data.llm_provider ?? "model"} calls · ${num.format(
                  data.llm_input_tokens + data.llm_output_tokens,
                )} tokens`}
          </div>
        </div>
      </div>

      <div className="banner banner--info">
        <span className="banner__icon">
          <span aria-hidden>i</span>
        </span>
        <div className="banner__body">
          <strong>Fill rate is {pct(fillRate)}, not 100% — on purpose.</strong> A system that fills
          every cell at 70% accuracy costs an analyst a full re-check of everything, which is the
          problem we set out to solve. The {num.format(data.provenance_counts.GAP)} blank cells are
          ones where no evidence supported a value, so none was written.
        </div>
      </div>

      <div className="grid-2">
        <section className="card">
          <div className="card__head">
            <div className="eyebrow eyebrow--dark">Provenance</div>
            <div className="card__title">Where every value came from</div>
            <div className="card__hint">
              Four tiers of evidence, plus the cells we deliberately left blank
            </div>
          </div>
          <div className="card__body">
            <ProvenanceBar counts={data.provenance_counts} />
          </div>
        </section>

        <section className="card">
          <div className="card__head">
            <div className="eyebrow eyebrow--dark">Confidence</div>
            <div className="card__title">Confidence across populated cells</div>
            <div className="card__hint">
              Raw, not yet calibrated — the delivery format ships only 2 labelled rows, which is
              not enough to fit a calibration curve against
            </div>
          </div>
          <div className="card__body">
            <ConfidenceHistogram buckets={data.confidence_histogram} />
          </div>
        </section>
      </div>

      <section className="card" style={{ marginTop: 20 }}>
        <div className="card__head">
          <div className="eyebrow eyebrow--dark">Compliance</div>
          <div className="card__title">Checks that hold without ground truth</div>
          <div className="card__hint">
            These measure our own output, so they are available today — accuracy figures are not,
            until a hand-labelled set exists
          </div>
        </div>
        <div className="card__body">
          <div className="tiles" style={{ margin: 0 }}>
            <div className="tile">
              <div className="tile__label">Vocabulary conformance</div>
              <div className="tile__value">{pct(data.lov_conformance)}</div>
              <div className="tile__foot">Values inside the approved list for their category</div>
            </div>
            <div className="tile">
              <div className="tile__label">Character limits</div>
              <div className="tile__value">{pct(data.char_limit_compliance)}</div>
              <div className="tile__foot">
                INVOICE_DESC ≤ 40 chars — asserted in tests, so it is 100% or the build fails
              </div>
            </div>
            <div className="tile">
              <div className="tile__label">Columns emitted</div>
              <div className="tile__value">252</div>
              <div className="tile__foot">Full delivery format, original header order</div>
            </div>
            <div className="tile">
              <div className="tile__label">Cells populated</div>
              <div className="tile__value">{num.format(data.cells_populated)}</div>
              <div className="tile__foot">of {num.format(data.cells_total)} total</div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
