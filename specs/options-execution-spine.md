# Spec — Options Execution Spine

Status: **draft, awaiting clarify answers**
Owner: Hamza
Branch: `feat/options-execution-spine`

Behaviour only. No libraries, file layout, or tech choices — those live in `plans/`.

## Goal

AlphaBeater can currently form a view but cannot act on one. This feature gives it hands: it turns a
directional view into a single concrete options position in an Alpaca **paper** account, refuses any
position that breaks a hard risk rule, and writes down every decision so the run can be audited and so
later versions can learn from the record.

Without it the project satisfies none of the hackathon's mandatory requirements (Trading API, options,
dedicated paper account) and produces no P&L, which is a judged criterion.

## User scenarios

1. The agent holds the view "SPY likely up over the next 5 days". It produces a concrete option order —
   one contract, a side, a whole-number quantity, a limit price — plus a written reason, and submits it
   to the paper account.
2. A proposed order would cost more than the per-trade cap. The gate rejects it, records a reason code,
   and nothing is sent.
3. The market is closed. The agent records its decision and sends no order.
4. The day's losses breach the daily stop. Every later proposal that day is rejected without evaluation.
5. An operator opens one journal file and sees every decision, order, and account value for the run.
6. An operator flips the kill switch. No new orders are sent, and the reason is recorded.
7. An open position reaches its horizon or its stop. The agent closes it and records the realized result.
8. An operator opens a dashboard and sees the equity curve and every trade with its reason.

## Functional requirements

**Planning**

1. A trade plan must name exactly one option contract, a side, an integer quantity, a limit price, and a
   time-in-force of `day` or `gtc`. Notional orders and extended-hours flags must never be produced.
2. The planner must select a call for an upward view and a put for a downward view.
3. The planner must select the nearest listed expiry that is on or after the view's horizon.
4. The planner must select a strike by target delta, and record the delta it actually got.
5. Every plan must carry the reason it exists — the view it came from, in words.

**Risk gate**

6. Every plan must pass the risk gate before any order is sent. There must be no code path that reaches
   submission without a recorded risk decision.
7. The gate must reject a plan when any of these is true, each with its own machine-readable reason code:
   - estimated cost exceeds the per-trade cap, as a percentage of account equity
   - open position count is at or above the cap
   - the day's realized plus unrealized loss is at or beyond the daily stop
   - the contract's bid-ask spread is wider than the configured fraction of its mid price
   - the contract's open interest or volume is below the configured floor
   - required quote or Greeks data is missing
   - account equity cannot be read
   - the market is closed
   - the kill switch is on
   - the account is not a paper account
8. A rejection must record a reason code and the measured value that triggered it, not only a log line.
9. An approval may resize the quantity downward. It must never resize upward.
10. The gate's limits must be readable from configuration without editing code.

**Execution**

11. Order submission must go through the tooling the hackathon requires, and the exact request sent and
    the exact response received must both be stored verbatim.
12. A submitted order must be recorded with the broker's own order id.
13. A partial fill, rejection, or cancellation must be recorded as what actually happened. The system must
    never assume a fill it has not observed.
14. The system must refuse to start against a non-paper account, and must verify this against the broker
    rather than trusting local configuration alone.

**Exits**

15. An open position must be closed when it reaches its horizon date, its profit target, or its stop loss.
16. A close must be recorded with its realized result.

**Journal**

17. Every run must append to a durable journal: timestamp, the view, the plan, the risk decision, the
    order request and response, and account equity.
18. Account equity must be sampled at least once per run so a P&L curve can be drawn over time.
19. The journal must be append-only. Nothing already written may be rewritten.

## Edge cases & rules

- **No option chain returned, or the underlying has no listed options** → reject with a reason code; do not crash.
- **Market closed or a holiday** → record the decision, send nothing.
- **The same contract is proposed twice in one day** → do not stack; treat the second as a duplicate and reject.
- **Broker request times out** → record the outcome as unknown and require a reconciliation read before any
  further order for that contract. Never blind-retry into a double order.
- **Greeks or implied volatility missing from the snapshot** → treat as failing the liquidity rule; reject.
- **Equity unreadable** → cannot size a trade; reject.
- **Quantity rounds to zero** after the per-trade cap is applied → reject rather than sending a zero order.
- **Kill switch flipped mid-run** → stop before the next submission, not after.
- **Journal file unwritable** → refuse to submit. An unrecorded order is worse than no order.

## Out of scope

- Live or real-money trading. Explicitly forbidden.
- Multi-leg spreads. Single-leg long calls and puts only in v1.
- The DSL calculator and backtest engine. Separate workstream.
- Automatic learning or model retraining. The journal makes it possible later; this feature does not do it.
- Portfolio-level optimization or hedging.
- Any human-facing order entry. The dashboard is read-only.

## Acceptance criteria

- [ ] `pytest` passes, including new tests.
- [ ] A test proves no order can be submitted without a recorded risk decision.
- [ ] A test exists for every rejection reason code in requirement 7, and each one fires.
- [ ] A dry-run mode produces a complete plan and risk decision with no network calls.
- [ ] A test proves a non-paper account halts startup.
- [ ] One real order is placed in the dedicated paper account and is visible in the Alpaca dashboard.
- [ ] The journal contains that order end-to-end: view, plan, decision, request, response, equity.
- [ ] The dashboard renders the equity curve and the trade table, and has been viewed in a browser.
- [ ] `README.md` no longer claims the project submits no orders.
