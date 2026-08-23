import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ConfidenceHistogram, ProvenanceBar } from "@/components/Charts";

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;
const num = new Intl.NumberFormat("en-US");

export default function Dashboard() {
  const { data, isLoading } = useQuery({ queryKey: ["run"], queryFn: api.getRunStats });

  if (isLoading || !data) {
    return (
      <>
        <div className="hero">
          <div className="skeleton" style={{ width: 180, opacity: 0.3 }} />
          <div className="skeleton" style={{ height: 40, width: "55%", marginTop: 16, opacity: 0.3 }} />
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
          <div className="tile__label">Analyst-hours saved</div>
          <div className="tile__value">{data.analyst_hours_saved}</div>
          <div className="tile__foot">Against a baseline of ~15 SKUs per analyst per day</div>
        </div>
        <div className="tile tile--blue">
          <div className="tile__label">Cost for this run</div>
          <div className="tile__value">${data.cost_usd.toFixed(2)}</div>
          <div className="tile__foot">
            {data.llm_calls} model calls — templates amortise across each family
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
            <div className="eyebrow eyebrow--dark">Calibration</div>
            <div className="card__title">Confidence across populated cells</div>
            <div className="card__hint">
              Calibrated on the labelled rows, so 90% confidence means 90% correct
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
