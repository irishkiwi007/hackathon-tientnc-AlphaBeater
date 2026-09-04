# Plan — Options Execution Spine

Implements `specs/options-execution-spine.md`. This is the **how**.

Clarify answers baked in: fully autonomous with a kill switch · aggressive caps
(5% per trade / 8 open positions / −15% daily stop) · CLI for orders, MCP registered for the demo.

## Shape

```
src/alphabeater/
  broker/
    market.py      read-only: account, clock, option chain, option snapshot
    cli.py         write: place/close orders by invoking the Alpaca Trading CLI
  strategy/
    options.py     View -> TradePlan  (expiry from horizon, strike from target delta)
  risk/
    limits.py      RiskLimits, loaded from config
    gate.py        RiskGate: TradePlan -> RiskDecision
  journal.py       append-only JSONL writer + reader
  runner.py        the loop: view -> plan -> gate -> execute -> journal
  dashboard.py     renders a static HTML equity curve + trade table from the journal
  models.py        += TradePlan, RiskDecision, ExecutionRecord, RejectionReason
```

Reused as-is: `StrictModel`, `Direction`, `Settings.assert_paper_trading()`, and
`MarketHypothesis` — its `expected_direction` + `horizon_days` are already exactly the planner's
inputs, so the existing LLM agents feed this with no reshaping.

## Key decisions

| Decision | Why | Trade-off |
|---|---|---|
| **Orders via the Trading CLI subprocess** | Satisfies the mandatory-tool rule and yields a verbatim audit trail — every order is a logged command and a logged response | Parsing a CLI is more brittle than an SDK. Mitigated by storing raw stdout/stderr and reconciling with a read-back before any retry |
| **Market data via REST/`alpaca-py`, not the CLI** | Chains, Greeks and IV are read-heavy and structured; the SDK is far less fragile here | One new dependency. Justified: it is the official SDK |
| **Journal as append-only JSONL** | Trivially append-only (spec req 19), human-readable, diffable, and directly renderable | No querying. Irrelevant at this scale |
| **Static HTML dashboard generated from the journal** | Nothing to keep running; opens straight in Chrome and screenshots cleanly for the demo video | Refresh means regenerate |
| **Kill switch = a file on disk** | Works mid-loop, needs no restart or redeploy, and a teammate can trip it without touching code | Filesystem coupling. Acceptable |
| **Paper check hits the broker, not the env var** | Spec req 14. A local flag can lie; the account endpoint cannot | One extra call at startup |
| **v1 view source: LLM hypothesis, with a deterministic momentum fallback** | Keeps the AI in the loop while guaranteeing the loop still trades if the model is slow, rate-limited, or returns junk | Two code paths to test |

## Build order

Each step is committed separately so any step has a clean rollback point. Steps 1–3 and 5 are pure and
fully testable with no network.

1. **Models** — `TradePlan`, `RiskDecision`, `ExecutionRecord`, `RejectionReason` enum, + tests
2. **Journal** — append-only JSONL, refuses to overwrite, + tests
3. **Risk gate** — every reason code from spec req 7, + a test per code
4. **Market adapter** — account, clock, chain, snapshot
5. **Options planner** — expiry-from-horizon and strike-from-delta, tested against a fixture chain
6. **CLI broker** — place/close, dry-run mode, verbatim capture
7. **Runner** — wire it together; assert paper account at startup; kill-switch check before each submit
8. **First real paper order** ← the P&L clock starts here
9. **Exits** — horizon, target, stop
10. **Dashboard** — render, then verify in Chrome
11. **Housekeeping** — fix the README's "submits no orders" claim, register the MCP server for the demo, push, update the team lead

Critical path for the deadline is 1–8. Everything after is polish that raises the score.

## Verification

Acceptance criteria from the spec become real checks:

- Steps 1–3, 5 → unit tests, run on every commit
- "No submission without a risk decision" → a test that asserts the runner raises when the gate is bypassed
- "Non-paper halts startup" → a test with a stubbed live-account response
- "One real order end-to-end" → manual, confirmed in the Alpaca dashboard and in the journal
- "Dashboard renders" → opened and screenshotted in Chrome
