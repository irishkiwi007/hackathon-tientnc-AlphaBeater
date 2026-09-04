"use client";

import { useEffect, useMemo, useState } from "react";
import runData from "./data/run.json";

/* Every number on this page comes from the committed audit record in
   web/app/data/run.json, written by `alphabeater-publish` from an actual run.
   Nothing here is hand-entered. */

type Metrics = {
  observations: number;
  total_return: number;
  benchmark_return: number;
  excess_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
};

type Candidate = {
  name: string;
  expression: string;
  rationale: string;
  expected_direction: string;
  selected: boolean;
  development_eligible: boolean;
  development_backtest: { validation: Metrics };
};

type Check = {
  name: string;
  passed: boolean;
  actual: string | number | boolean | null;
  limit: string | number | boolean | null;
  blocking: boolean;
};

type Run = {
  run_at: string;
  execution_policy: string | null;
  research_qualified: boolean | null;
  candidates: Candidate[];
  selected_backtest: { holdout: Metrics } | null;
  trade_plan: Record<string, string | number | null> | null;
  risk: {
    approved: boolean;
    checks: Check[];
    rejected_reasons: string[];
    advisory_reasons: string[];
  } | null;
  order: unknown | null;
  observation: { universe: string[]; evidence: string[] };
  hypothesis: { title: string; mechanism: string } | null;
  research_protocol: { generator_model: string; candidate_count: number };
  monitor: { open_orders: number; positions: number; market_open: boolean };
};

const run = runData as unknown as Run;

const stages = ["Observe", "Hypothesize", "Factor", "Backtest", "Plan", "Risk"];

const pct = (value: number, digits = 2) =>
  `${value > 0 ? "+" : ""}${(value * 100).toFixed(digits)}%`;

const num = (value: unknown) => Number(value ?? 0);

const dateLabel = new Date(run.run_at)
  .toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })
  .toUpperCase();

export default function Home() {
  const checks = run.risk?.checks ?? [];
  const passedChecks = checks.filter((check) => check.passed).length;
  const blockingFailures = checks.filter((check) => !check.passed && check.blocking);
  const advisoryFailures = checks.filter((check) => !check.passed && !check.blocking);

  const selectedIndex = Math.max(
    0,
    run.candidates.findIndex((item) => item.selected),
  );
  const [candidateIndex, setCandidateIndex] = useState(selectedIndex);
  const [phase, setPhase] = useState(stages.length);
  const [running, setRunning] = useState(false);
  const [view, setView] = useState<"overview" | "audit">("overview");

  const candidate = run.candidates[candidateIndex];
  const validation = candidate.development_backtest.validation;
  const holdout = run.selected_backtest?.holdout;
  const plan = run.trade_plan;

  const maxLoss = num(plan?.maximum_loss);
  const [riskPct, setRiskPct] = useState(0.5);
  const allowedLoss = riskPct * 1000; // 0.5% of the $100,000 paper account
  const premiumPasses = allowedLoss >= maxLoss;

  useEffect(() => {
    if (!running || phase >= stages.length) return;
    const timer = window.setTimeout(() => {
      setPhase((value) => value + 1);
      if (phase + 1 >= stages.length) setRunning(false);
    }, 520);
    return () => window.clearTimeout(timer);
  }, [phase, running]);

  const replay = () => {
    setPhase(0);
    setRunning(true);
    setView("overview");
  };

  const barScale = useMemo(() => {
    if (!holdout) return 10;
    return Math.max(
      Math.abs(holdout.total_return * 100),
      Math.abs(holdout.benchmark_return * 100),
      10,
    );
  }, [holdout]);

  const right = String(plan?.right ?? "").toUpperCase();

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="AlphaBeater home">
          <span className="brand-mark">α</span>
          <span>AlphaBeater</span>
        </a>
        <div className="top-actions">
          <span className="paper-pill">
            <i /> Alpaca paper
          </span>
          <a
            className="ghost-button"
            href="https://github.com/tientnc/AlphaBeater"
            target="_blank"
            rel="noreferrer"
          >
            View code ↗
          </a>
        </div>
      </header>

      <section className="hero" id="top">
        <div className="hero-backdrop" />
        <div className="hero-copy">
          <div className="eyebrow">
            <span>AUDITED RUN RECORD</span>
            <b>{dateLabel}</b>
          </div>
          <h1>
            Research a signal.
            <br />
            <em>Trade only if it earns trust.</em>
          </h1>
          <p>
            An open-source model turns market evidence into testable factors. Deterministic code
            backtests them, chooses a defined-risk option, and lets Alpaca execute only after every
            hard check. This page renders one real run — including the parts that failed.
          </p>
          <div className="hero-actions">
            <button className="primary-button" onClick={replay} disabled={running}>
              {running
                ? `Running ${stages[Math.min(phase, stages.length - 1)]}...`
                : "Replay agent run"}
            </button>
            <button className="text-button" onClick={() => setView("audit")}>
              Inspect audit trail <span>↓</span>
            </button>
          </div>
        </div>
        <div className="run-card">
          <div className="run-card-head">
            <div>
              <span className="muted">CURRENT RUN</span>
              <strong>{run.research_protocol.generator_model}</strong>
            </div>
            <span className="status held">
              <i /> {run.risk?.approved ? "APPROVED" : "HELD"}
            </span>
          </div>
          <div className="run-stat-grid">
            <div>
              <span>Candidates tested</span>
              <b>{run.research_protocol.candidate_count}</b>
            </div>
            <div>
              <span>Risk checks</span>
              <b>
                {passedChecks} / {checks.length}
              </b>
            </div>
            <div>
              <span>Max loss</span>
              <b>${maxLoss.toFixed(0)}</b>
            </div>
            <div>
              <span>Order</span>
              <b>{run.order ? "Submitted" : "Not sent"}</b>
            </div>
          </div>
          {blockingFailures.map((check, index) => (
            <div className="hold-reason" key={check.name}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div>
                <b>{check.name} blocked execution</b>
                <p>
                  Measured {String(check.actual)}, limit {String(check.limit)}. The plan was kept
                  and the order was never sent.
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="pipeline-section">
        <div className="section-heading">
          <div>
            <span className="kicker">AGENT PIPELINE</span>
            <h2>One decision, six inspectable stages</h2>
          </div>
          <div className="segmented">
            <button
              className={view === "overview" ? "active" : ""}
              onClick={() => setView("overview")}
            >
              Overview
            </button>
            <button className={view === "audit" ? "active" : ""} onClick={() => setView("audit")}>
              Audit log
            </button>
          </div>
        </div>

        {view === "overview" ? (
          <>
            <div className="stage-row" aria-label="Pipeline stages">
              {stages.map((stage, index) => (
                <div
                  className={`stage ${index < phase ? "done" : index === phase ? "active" : ""}`}
                  key={stage}
                >
                  <span>{index < phase ? "✓" : String(index + 1).padStart(2, "0")}</span>
                  <b>{stage}</b>
                </div>
              ))}
            </div>

            <div className="dashboard-grid">
              <article className="panel factor-panel">
                <div className="panel-title">
                  <div>
                    <span className="kicker">FACTOR EVALUATION</span>
                    <h3>Locked holdout performance</h3>
                  </div>
                  <span className="tag">{holdout?.observations ?? 0} sessions</span>
                </div>
                <div className="candidate-tabs">
                  {run.candidates.map((item, index) => (
                    <button
                      key={item.name}
                      className={candidateIndex === index ? "active" : ""}
                      onClick={() => setCandidateIndex(index)}
                      title={item.rationale}
                    >
                      <span>{String(index + 1).padStart(2, "0")}</span>
                      {item.name.replaceAll("_", " ")}
                    </button>
                  ))}
                </div>
                <code>{candidate.expression}</code>
                <div className="metric-row">
                  <div>
                    <span>Validation return</span>
                    <b className={validation.total_return >= 0 ? "positive" : ""}>
                      {pct(validation.total_return)}
                    </b>
                  </div>
                  <div>
                    <span>vs benchmark</span>
                    <b>{pct(validation.excess_return)}</b>
                  </div>
                  <div>
                    <span>Sharpe</span>
                    <b>{validation.sharpe_ratio.toFixed(2)}</b>
                  </div>
                  <div>
                    <span>Max drawdown</span>
                    <b>{pct(validation.max_drawdown)}</b>
                  </div>
                </div>
                <div className={`gate-result ${candidate.development_eligible ? "pass" : "fail"}`}>
                  <span>{candidate.development_eligible ? "✓" : "×"}</span>
                  <div>
                    <b>
                      {candidate.development_eligible
                        ? "Passed the research gate"
                        : "Rejected by the research gate"}
                    </b>
                    <small>
                      {candidate.development_eligible
                        ? "Positive and stable across training and validation."
                        : "Required positive excess return and Sharpe ≥ 0.50 in both periods."}
                    </small>
                  </div>
                </div>
                {holdout && (
                  <div className="bar-chart" aria-label="Locked holdout comparison">
                    <div className={`bar-line ${holdout.total_return < 0 ? "loss" : ""}`}>
                      <span>Factor</span>
                      <div>
                        <i
                          style={{
                            width: `${(Math.abs(holdout.total_return * 100) / barScale) * 100}%`,
                          }}
                        />
                      </div>
                      <b className={holdout.total_return < 0 ? "loss" : ""}>
                        {(holdout.total_return * 100).toFixed(2)}%
                      </b>
                    </div>
                    <div
                      className={`bar-line benchmark ${holdout.benchmark_return < 0 ? "loss" : ""}`}
                    >
                      <span>Buy and hold</span>
                      <div>
                        <i
                          style={{
                            width: `${(Math.abs(holdout.benchmark_return * 100) / barScale) * 100}%`,
                          }}
                        />
                      </div>
                      <b>{(holdout.benchmark_return * 100).toFixed(2)}%</b>
                    </div>
                  </div>
                )}
                <p className="fineprint">
                  Includes 5 bps estimated transaction cost. No candidate qualified, so the locked
                  holdout is shown for transparency, not as a result to trade on.
                </p>
              </article>

              <article className="panel trade-panel">
                <div className="panel-title">
                  <div>
                    <span className="kicker">OPTIONS PLAN</span>
                    <h3>
                      {String(plan?.underlying ?? "")} long {right.toLowerCase()}
                    </h3>
                  </div>
                  <span className={`tag ${right === "CALL" ? "call" : ""}`}>{right}</span>
                </div>
                <div className="contract">
                  {String(plan?.underlying ?? "")} <b>{String(plan?.expiration ?? "")}</b>{" "}
                  {String(plan?.strike ?? "")} {right.charAt(0)}
                </div>
                <div className="trade-price">
                  <span>${num(plan?.limit_price).toFixed(2)}</span>
                  <small>
                    limit price
                    <br />${maxLoss.toFixed(0)} max loss
                  </small>
                </div>
                <dl className="trade-details">
                  <div className="wide">
                    <dt>Factor</dt>
                    <dd>{String(plan?.factor_name ?? "")}</dd>
                  </div>
                  <div>
                    <dt>Delta</dt>
                    <dd>{num(plan?.delta).toFixed(4)}</dd>
                  </div>
                  <div>
                    <dt>Strike</dt>
                    <dd>${num(plan?.strike).toFixed(2)}</dd>
                  </div>
                  <div>
                    <dt>Bid / ask</dt>
                    <dd>
                      ${num(plan?.bid_price).toFixed(2)} / ${num(plan?.ask_price).toFixed(2)}
                    </dd>
                  </div>
                  <div>
                    <dt>Spread</dt>
                    <dd>{(num(plan?.relative_spread) * 100).toFixed(1)}%</dd>
                  </div>
                  <div>
                    <dt>Quantity</dt>
                    <dd>{num(plan?.quantity)} contract</dd>
                  </div>
                  <div>
                    <dt>Intent</dt>
                    <dd>Buy to open</dd>
                  </div>
                </dl>
                <div className="order-route">
                  <span>MCP</span>
                  <div>
                    <b>Official Alpaca MCP</b>
                    <small>place_option_order · paper=true</small>
                  </div>
                  <i>→</i>
                </div>
              </article>
            </div>

            <div className="risk-layout">
              <article className="panel risk-controls">
                <div className="panel-title">
                  <div>
                    <span className="kicker">RISK SANDBOX</span>
                    <h3>Test the maximum-loss gate</h3>
                  </div>
                  <span className={`status ${premiumPasses ? "ready" : "blocked"}`}>
                    {premiumPasses ? "PASSES" : "BLOCKED"}
                  </span>
                </div>
                <p>
                  Adjust the per-trade account risk limit. The contract premium is always the
                  maximum loss for this long-option strategy.
                </p>
                <div className="slider-label">
                  <span>Risk per trade</span>
                  <b>
                    {riskPct.toFixed(2)}% · ${allowedLoss.toFixed(0)}
                  </b>
                </div>
                <input
                  aria-label="Risk per trade"
                  type="range"
                  min="0.20"
                  max="1.00"
                  step="0.05"
                  value={riskPct}
                  onChange={(event) => setRiskPct(Number(event.target.value))}
                />
                <div className="range-ends">
                  <span>0.20%</span>
                  <span>1.00%</span>
                </div>
                <div className={`gate-result ${premiumPasses ? "pass" : "fail"}`}>
                  <span>{premiumPasses ? "✓" : "×"}</span>
                  <div>
                    <b>
                      ${maxLoss.toFixed(0)} {premiumPasses ? "is inside" : "exceeds"} the limit
                    </b>
                    <small>
                      {premiumPasses
                        ? `$${(allowedLoss - maxLoss).toFixed(0)} risk capacity remains`
                        : `Reduce premium by $${(maxLoss - allowedLoss).toFixed(0)}`}
                    </small>
                  </div>
                </div>
              </article>

              <article className="panel checks-panel">
                <div className="checks-head">
                  <div>
                    <span className="kicker">HARD CHECKS</span>
                    <h3>
                      {passedChecks} passed · {blockingFailures.length} blocking ·{" "}
                      {advisoryFailures.length} advisory
                    </h3>
                  </div>
                  <span className="ring">
                    {passedChecks}
                    <small>/{checks.length}</small>
                  </span>
                </div>
                <div className="checks-grid">
                  {checks.map((check) => (
                    <div
                      className={
                        check.passed ? "check" : check.blocking ? "check failed" : "check held-check"
                      }
                      key={check.name}
                    >
                      <i>{check.passed ? "✓" : check.blocking ? "×" : "!"}</i>
                      <span>
                        <b>{check.name}</b>
                        <small>
                          {String(check.actual)} / {String(check.limit)}
                        </small>
                      </span>
                    </div>
                  ))}
                </div>
                <p className="fineprint">
                  Blocking checks stop an order outright. Advisory checks are recorded but do not
                  block in the labelled experimental-forward mode.
                </p>
              </article>
            </div>
          </>
        ) : (
          <AuditLog />
        )}
      </section>

      <section className="monitor-strip">
        <div>
          <span className="kicker">AUTONOMOUS MONITOR</span>
          <h2>It watches after the order too.</h2>
        </div>
        <div className="monitor-rules">
          <div>
            <span>-25%</span>
            <b>Stop loss</b>
            <small>Sell to close</small>
          </div>
          <div>
            <span>+40%</span>
            <b>Take profit</b>
            <small>Lock gains</small>
          </div>
          <div>
            <span>7 DTE</span>
            <b>Expiry exit</b>
            <small>Avoid final week</small>
          </div>
          <div>
            <span>15 MIN</span>
            <b>Stale order</b>
            <small>Cancel entry</small>
          </div>
        </div>
      </section>

      <footer>
        <div className="brand">
          <span className="brand-mark">α</span>
          <span>AlphaBeater</span>
        </div>
        <p>Experimental paper-trading software. Not financial advice.</p>
        <span>Featherless · Gemma · Alpaca Market Data · Alpaca MCP</span>
      </footer>
    </main>
  );
}

function AuditLog() {
  const checks = run.risk?.checks ?? [];
  const eligible = run.candidates.filter((item) => item.development_eligible).length;
  const rows: [string, string][] = [
    ["OBSERVE", `Read Alpaca IEX bars for ${run.observation.universe.join(", ")}.`],
    ["IDEA", run.hypothesis ? run.hypothesis.title : "No hypothesis recorded."],
    [
      "FACTOR",
      `Validated ${run.research_protocol.candidate_count} generated expressions against the safe DSL. No eval used.`,
    ],
    [
      "BACKTEST",
      `${eligible} of ${run.candidates.length} candidates passed the research gate. Policy: ${run.execution_policy ?? "n/a"}.`,
    ],
    [
      "OPTIONS",
      run.trade_plan
        ? `Selected ${String(run.trade_plan.contract_symbol)} at a $${num(run.trade_plan.limit_price).toFixed(2)} limit.`
        : "No contract selected.",
    ],
    [
      "RISK",
      run.risk?.approved
        ? `Approved after ${checks.length} checks.`
        : `Rejected: ${(run.risk?.rejected_reasons ?? []).join(", ") || "none"}.`,
    ],
    [
      "MONITOR",
      `Paper account: ${run.monitor.open_orders} open orders, ${run.monitor.positions} positions.`,
    ],
  ];
  return (
    <article className="panel audit-panel">
      <div className="panel-title">
        <div>
          <span className="kicker">IMMUTABLE RUN RECORD</span>
          <h3>Decision audit trail</h3>
        </div>
        <span className="tag">{new Date(run.run_at).toISOString().slice(0, 19)}Z</span>
      </div>
      <div className="audit-list">
        {rows.map(([type, message], index) => (
          <div className="audit-row" key={type}>
            <span>STAGE {index + 1}</span>
            <b>{type}</b>
            <p>{message}</p>
            <i>{String(index + 1).padStart(2, "0")}</i>
          </div>
        ))}
      </div>
    </article>
  );
}
