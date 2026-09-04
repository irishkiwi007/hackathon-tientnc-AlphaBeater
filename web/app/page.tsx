"use client";

import { useEffect, useMemo, useState } from "react";

const candidates = [
  {
    name: "small_cap_trend_divergence",
    expression: "sub(returns(close, 60), returns(close, 20))",
    holdoutReturn: 9.45,
    benchmark: 6.98,
    sharpe: 1.36,
    drawdown: -6.05,
  },
];

const stages = ["Observe", "Hypothesize", "Factor", "Backtest", "Plan", "Risk"];

const baseChecks = [
  ["Paper account active", "ACTIVE"],
  ["Paper-only trading", "Live trading disabled"],
  ["Options permission", "Level 3"],
  ["Contract quantity", "1 / 1"],
  ["Market open", "Yes"],
  ["No duplicate exposure", "None"],
  ["Single-trade maximum loss", "$414 / $500"],
  ["Portfolio option exposure", "$414 / $2,000"],
  ["Options buying power", "$414 / $100,000"],
  ["Daily loss kill switch", "0.00% / 2.00%"],
  ["Quote freshness", "0s / 900s"],
  ["Bid-ask spread", "1.2% / 20.0%"],
  ["Holdout sample", "87 / 60"],
  ["Holdout Sharpe", "1.36 / 0.50"],
  ["Holdout excess return", "+2.47% / > 0%"],
  ["Holdout drawdown", "-6.05% / -15.0%"],
] as const;

function formatPct(value: number) {
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

export default function Home() {
  const [candidateIndex, setCandidateIndex] = useState(0);
  const [riskPct, setRiskPct] = useState(0.5);
  const [phase, setPhase] = useState(stages.length);
  const [running, setRunning] = useState(false);
  const [view, setView] = useState<"overview" | "audit">("overview");
  const candidate = candidates[candidateIndex];
  const allowedLoss = riskPct * 1000;
  const premiumPasses = allowedLoss >= 414;
  const passedChecks = premiumPasses ? 16 : 15;

  useEffect(() => {
    if (!running) return;
    if (phase >= stages.length) return;
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

  const barScale = useMemo(
    () => Math.max(candidate.holdoutReturn, candidate.benchmark, 10),
    [candidate],
  );

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="AlphaBeater home">
          <span className="brand-mark">α</span>
          <span>AlphaBeater</span>
        </a>
        <div className="top-actions">
          <span className="paper-pill"><i /> Alpaca paper</span>
          <a className="ghost-button" href="https://github.com/tientnc/AlphaBeater" target="_blank" rel="noreferrer">
            View code ↗
          </a>
        </div>
      </header>

      <section className="hero" id="top">
        <div className="hero-backdrop" />
        <div className="hero-copy">
          <div className="eyebrow"><span>RECORDED PAPER RUN</span><b>SEPT 3, 2026</b></div>
          <h1>Research a signal.<br /><em>Trade only if it earns trust.</em></h1>
          <p>
            Gemma turns market evidence into testable factors. Deterministic code backtests,
            chooses a defined-risk option, and lets Alpaca execute only after every hard check.
          </p>
          <div className="hero-actions">
            <button className="primary-button" onClick={replay} disabled={running}>
              {running ? `Running ${stages[Math.min(phase, stages.length - 1)]}...` : "Replay agent run"}
            </button>
            <button className="text-button" onClick={() => setView("audit")}>Inspect audit trail <span>↓</span></button>
          </div>
        </div>
        <div className="run-card">
          <div className="run-card-head">
            <div><span className="muted">EXECUTED RUN</span><strong>AB-20260903-01</strong></div>
            <span className="status ready"><i /> FILLED</span>
          </div>
          <div className="run-stat-grid">
            <div><span>Generated factors</span><b>15</b></div>
            <div><span>Risk checks</span><b>{passedChecks} / 16</b></div>
            <div><span>Max loss</span><b>$414</b></div>
            <div><span>Order</span><b>Filled</b></div>
          </div>
          <div className="hold-reason">
            <span>01</span>
            <div><b>Paper position is being monitored</b><p>Best observed unrealized paper P&amp;L: +$4.94 at a recorded point in time. Experimental forward-paper run; P&amp;L is volatile.</p></div>
          </div>
        </div>
      </section>

      <section className="pipeline-section">
        <div className="section-heading">
          <div><span className="kicker">AGENT PIPELINE</span><h2>One decision, six inspectable stages</h2></div>
          <div className="segmented">
            <button className={view === "overview" ? "active" : ""} onClick={() => setView("overview")}>Overview</button>
            <button className={view === "audit" ? "active" : ""} onClick={() => setView("audit")}>Audit log</button>
          </div>
        </div>

        {view === "overview" ? (
          <>
            <div className="stage-row" aria-label="Pipeline stages">
              {stages.map((stage, index) => (
                <div className={`stage ${index < phase ? "done" : index === phase ? "active" : ""}`} key={stage}>
                  <span>{index < phase ? "✓" : String(index + 1).padStart(2, "0")}</span>
                  <b>{stage}</b>
                </div>
              ))}
            </div>

            <div className="dashboard-grid">
              <article className="panel factor-panel">
                <div className="panel-title"><div><span className="kicker">FACTOR EVALUATION</span><h3>Holdout performance</h3></div><span className="tag">87 sessions</span></div>
                <div className="candidate-tabs">
                  {candidates.map((item, index) => (
                    <button key={item.name} className={candidateIndex === index ? "active" : ""} onClick={() => setCandidateIndex(index)}>
                      <span>0{index + 1}</span>{item.name.replaceAll("_", " ")}
                    </button>
                  ))}
                </div>
                <code>{candidate.expression}</code>
                <div className="metric-row">
                  <div><span>Holdout return</span><b className="positive">{formatPct(candidate.holdoutReturn)}</b></div>
                  <div><span>vs benchmark</span><b>{formatPct(candidate.holdoutReturn - candidate.benchmark)}</b></div>
                  <div><span>Sharpe</span><b>{candidate.sharpe.toFixed(2)}</b></div>
                  <div><span>Max drawdown</span><b>{formatPct(candidate.drawdown)}</b></div>
                </div>
                <div className="bar-chart" aria-label="Holdout return comparison">
                  <div className="bar-line"><span>Factor</span><div><i style={{width: `${candidate.holdoutReturn / barScale * 100}%`}} /></div><b>{candidate.holdoutReturn.toFixed(2)}%</b></div>
                  <div className="bar-line benchmark"><span>Equal weight</span><div><i style={{width: `${candidate.benchmark / barScale * 100}%`}} /></div><b>{candidate.benchmark.toFixed(2)}%</b></div>
                </div>
                <p className="fineprint">Includes 5 bps estimated transaction cost. The holdout is a recent time split, not a claim of future profitability.</p>
              </article>

              <article className="panel trade-panel">
                <div className="panel-title"><div><span className="kicker">EXECUTED PAPER ORDER</span><h3>IWM long call</h3></div><span className="tag call">CALL</span></div>
                <div className="contract">IWM <b>25 SEP 2026</b> 296 C</div>
                <div className="trade-price"><span>$4.14</span><small>filled limit<br />$414 max loss</small></div>
                <dl className="trade-details">
                  <div><dt>Signal strength</dt><dd>0.65</dd></div>
                  <div><dt>Delta</dt><dd>+0.4858</dd></div>
                  <div><dt>Bid / ask</dt><dd>$4.11 / $4.16</dd></div>
                  <div><dt>Spread</dt><dd>1.2%</dd></div>
                  <div><dt>Quantity</dt><dd>1 contract</dd></div>
                  <div><dt>Best unrealized gain</dt><dd>+$4.94 observed</dd></div>
                </dl>
                <div className="order-route"><span>MCP</span><div><b>Official Alpaca MCP</b><small>place_option_order · paper=true</small></div><i>→</i></div>
              </article>
            </div>

            <div className="risk-layout">
              <article className="panel risk-controls">
                <div className="panel-title"><div><span className="kicker">RISK SANDBOX</span><h3>Test the maximum-loss gate</h3></div><span className={`status ${premiumPasses ? "ready" : "blocked"}`}>{premiumPasses ? "PASSES" : "BLOCKED"}</span></div>
                <p>Adjust the per-trade account risk limit. The contract premium is always the maximum loss for this long-option strategy.</p>
                <div className="slider-label"><span>Risk per trade</span><b>{riskPct.toFixed(2)}% · ${allowedLoss.toFixed(0)}</b></div>
                <input aria-label="Risk per trade" type="range" min="0.20" max="1.00" step="0.05" value={riskPct} onChange={(event) => setRiskPct(Number(event.target.value))} />
                <div className="range-ends"><span>0.20%</span><span>1.00%</span></div>
                <div className={`gate-result ${premiumPasses ? "pass" : "fail"}`}>
                  <span>{premiumPasses ? "✓" : "×"}</span>
                  <div><b>{premiumPasses ? "$414 is inside the limit" : "$414 exceeds the limit"}</b><small>{premiumPasses ? `$${(allowedLoss - 414).toFixed(0)} risk capacity remains` : `Reduce premium by $${(414 - allowedLoss).toFixed(0)}`}</small></div>
                </div>
              </article>
              <article className="panel checks-panel">
                <div className="checks-head"><div><span className="kicker">EXECUTION CHECKS</span><h3>{passedChecks} passed · {16 - passedChecks} blocked</h3></div><span className="ring">{passedChecks}<small>/16</small></span></div>
                <div className="checks-grid">
                  {baseChecks.map(([label, value], index) => {
                    const riskCheck = index === 6;
                    const pass = !riskCheck || premiumPasses;
                    return <div className={pass ? "check" : "check failed"} key={label}><i>{pass ? "✓" : "×"}</i><span><b>{label}</b><small>{riskCheck ? `$414 / $${allowedLoss.toFixed(0)}` : value}</small></span></div>;
                  })}
                </div>
              </article>
            </div>
          </>
        ) : (
          <AuditLog />
        )}
      </section>

      <section className="monitor-strip">
        <div><span className="kicker">AUTONOMOUS MONITOR</span><h2>It watches after the order too.</h2></div>
        <div className="monitor-rules">
          <div><span>-25%</span><b>Stop loss</b><small>Sell to close</small></div>
          <div><span>+40%</span><b>Take profit</b><small>Lock gains</small></div>
          <div><span>7 DTE</span><b>Expiry exit</b><small>Avoid final week</small></div>
          <div><span>15 MIN</span><b>Stale order</b><small>Cancel entry</small></div>
        </div>
      </section>

      <footer>
        <div className="brand"><span className="brand-mark">α</span><span>AlphaBeater</span></div>
        <p>Experimental paper-trading software. Not financial advice.</p>
        <span>Gemma · Alpaca Market Data · Alpaca MCP</span>
      </footer>
    </main>
  );
}

function AuditLog() {
  const rows = [
    ["11:11:53", "OBSERVE", "Fetched 290 daily bars for SPY, QQQ, and IWM from Alpaca IEX."],
    ["11:11:54", "IDEA", "Gemma generated three falsifiable market hypotheses."],
    ["11:11:55", "FACTOR", "Validated 15 generated expressions against the safe DSL. No eval used."],
    ["11:11:56", "BACKTEST", "Selected small_cap_trend_divergence for a controlled forward-paper experiment."],
    ["11:15:13", "OPTIONS", "Selected IWM260925C00296000 at a $4.14 limit and $414 maximum loss."],
    ["11:15:32", "RISK", "All 16 execution checks passed under the experimental forward-paper policy."],
    ["11:17:04", "MONITOR", "Order filled. Best recorded unrealized paper P&L reached +$4.94 at a point in time."],
  ];
  return (
    <article className="panel audit-panel">
      <div className="panel-title"><div><span className="kicker">IMMUTABLE RUN RECORD</span><h3>Decision audit trail</h3></div><span className="tag">JSON artifact</span></div>
      <div className="audit-list">
        {rows.map(([time, type, message], index) => <div className="audit-row" key={type}><span>{time}</span><b>{type}</b><p>{message}</p><i>{String(index + 1).padStart(2, "0")}</i></div>)}
      </div>
    </article>
  );
}
