# AlphaBeater

AlphaBeater is an autonomous, risk-gated options agent built for the Alpaca AI Trading Agents Hackathon. It uses Gemma to form a market hypothesis and generate factor expressions, tests those expressions on Alpaca data, builds a defined-risk options plan, and routes an approved paper order through Alpaca's official MCP server.

The LLM does research. Regular Python code calculates factors, ranks contracts, and enforces every trading limit.

## Current workflow

1. Read recent SPY, QQQ, and IWM bars from Alpaca's IEX feed and summarize 5/20/60-day returns, price location, volatility, and relative volume.
2. Ask Gemma for a falsifiable hypothesis grounded in that snapshot.
3. Run three precommitted research batches. Each asks Gemma for a distinct hypothesis and five different factor candidates in the project's small factor DSL.
4. Validate and calculate each expression without `eval`.
5. Standardize each factor over the trailing 60 sessions, select the strongest absolute signal, and simulate its call/put direction with next-session underlying returns and 5 bps costs. Split observations chronologically into 50 percent training, 20 percent validation, and a locked 30 percent test period.
6. Reject candidates unless both training and validation have positive excess return, at least 0.50 Sharpe, and acceptable drawdown. Rank survivors using validation data only. Then evaluate the winner once on the locked test period.
7. Convert its current standardized signal into a long call or long put.
8. Search the Alpaca indicative option chain for 21 to 45 DTE, 0.35 to 0.60 absolute delta, a maximum 20 percent spread, and premium within the account risk budget.
9. Run 16 deterministic account, position, liquidity, loss, and backtest checks.
10. If `--execute` was explicitly supplied and all checks pass, submit one buy-to-open limit order to the Alpaca paper account through `place_option_order` on the official Alpaca MCP server.
11. Monitor open orders and positions for stale entries, stop loss, take profit, and expiry rules.

The strategy buys premium only. Its maximum loss is the premium paid. It does not write naked options or send live orders.

## Latest verified run

On September 3, 2026, Gemma 4 31B generated 15 valid, executable factor candidates. Seven had positive raw training returns and five had positive raw validation returns, but none were positive and stable in both periods after applying the full gate. The agent recorded `abstained_before_locked_test`, did not inspect the locked test, and did not construct or submit an order.

This is expected risk behavior, not a profitable result. The audit is stored locally in `artifacts/final-evaluation.json` and is excluded from Git because generated artifacts may contain account or order details.

## Research model and evaluation

Gemma `gemma-4-31b-it` generates independent hypotheses and five candidate DSL formulas per hypothesis. The five available precommitted themes are trend, mean reversion, volatility regime, price-volume confirmation, and breakout/range behavior. No predictive ML model is trained or fitted. Python calculates every factor and return deterministically.

The chronological split is 50/20/30. The first half checks initial consistency, the next 20 percent selects one candidate, and the last 30 percent is a locked test used only after selection. A failed locked test stops the run. Repeated runs against the same locked period must not be used to search for a passing result.

During hackathon development, the holdout was inspected while the evaluation algorithm itself was being corrected. Current results are therefore exploratory, not a publication-grade untouched test. A future paper should freeze the pipeline and collect a new forward test period.

The backtest is a directional underlying-return proxy for comparing factors. It does not reconstruct historical option-chain prices, implied volatility, or option fills. Paper execution supplies the separate end-to-end options evidence.

The complete protocol, period boundaries, model name, development metrics, selected test metrics, and risk decision are saved in `artifacts/latest-run.json`.

Use `--research-batches 1` through `5` to set the precommitted search size. The default is three. Batches are generated before the locked test is evaluated and never receive test feedback.

Use `--reuse-research artifacts/previous-run.json` to recalculate a saved candidate batch without spending Gemini quota or changing the precommitted formulas.

## Setup

Python 3.11 or newer and [uv](https://docs.astral.sh/uv/) are required. `uvx` launches Alpaca's MCP server without a separate server install.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
copy .env.example .env
```

Add a Google AI Studio key and Alpaca paper keys to `.env`. Never commit that file.

```dotenv
GEMINI_API_KEY=...
GEMMA_MODEL=gemma-4-31b-it
ALPACA_API_KEY=...
ALPACA_SECRET_KEY=...
ALPACA_PAPER=true
```

## Verify each integration

```bash
# Paper account and Gemma configuration
alphabeater-check

# Alpaca IEX bars and indicative options chain
alphabeater-data-check

# Official Alpaca MCP server and paper account
alphabeater-mcp-check

# Gemma hypothesis, factor calculation, and backtests
alphabeater-research-demo
```

`alphabeater-mcp-check --describe` also shows the available trading tool schemas. It sets `ALPACA_PAPER_TRADE=true` for the MCP child process.

## Run the complete agent

Preview mode performs every stage but cannot submit an order:

```bash
alphabeater-run
```

The full audit record is written to `artifacts/latest-run.json`.

Paper execution is explicit:

```bash
alphabeater-run --execute
```

Even with that flag, no order is sent unless all 16 risk checks pass. Live trading is rejected by configuration. Orders use deterministic client order IDs so retries cannot silently create a second position.

An explicitly unvalidated forward paper experiment is available for execution demonstrations:

```bash
alphabeater-run --execute --paper-experiment
```

This mode may promote the least unstable development candidate when none is research-qualified. Historical performance checks remain visible as non-blocking advisories. Account status, paper-only enforcement, market hours, duplicate exposure, quantity, premium loss, total exposure, buying power, daily loss, quote freshness, and spread remain blocking. The audit labels the execution policy `experimental_forward_paper`; it must not be described as validated or predictably profitable.

## Autonomous monitoring

One read-only check:

```bash
alphabeater-monitor
```

Continuous monitoring every 30 seconds:

```bash
alphabeater-monitor --watch --interval 30
```

By default, the monitor only records recommended actions. Set `ENABLE_AUTOMATIC_EXITS=true` in `.env` to let it cancel stale paper entry orders and submit sell-to-close paper orders when one of these rules fires:

- Position loss reaches 25 percent
- Position gain reaches 40 percent
- Contract reaches 7 DTE
- Entry limit order remains open for 15 minutes

Events are appended to `artifacts/trading-journal.jsonl`.
Each monitor report also records position cost basis, market value, unrealized paper P&L, and return percentage.

## Risk policy

- Paper account only
- Account must be active and unblocked
- Options approval level 2 or higher
- One contract per trade
- Maximum trade loss: 0.5 percent of equity
- Maximum total options exposure: 2 percent of equity
- Daily loss kill switch: 2 percent
- Maximum relative spread: 20 percent
- Maximum quote age: 15 minutes
- At least 60 holdout observations
- Holdout Sharpe at least 0.50
- Positive holdout excess return
- Holdout drawdown no worse than -15 percent
- No duplicate open order or position in the selected contract
- Market must be open for execution

The implementation is in `src/alphabeater/risk.py`. The LLM cannot modify this policy during a run.

## Dashboard

The interactive demo is in `web/`. It contains a sanitized copy of the latest run and no credentials.

```bash
cd web
npm install
npm run dev
```

## Tests

```bash
pytest
ruff check src tests
ruff format --check src tests

cd web
npm run lint
npm test
```

## Project layout

```text
src/alphabeater/
  agents/               Gemma idea and factor agents
  alpaca/               paper account and market data adapters
  agent_run.py          complete workflow
  backtest.py           factor evaluation
  dsl.py                safe expression parser
  execution.py          paper SDK order adapter
  mcp_check.py          official Alpaca MCP connection
  mcp_execution.py      MCP option order adapter
  monitor.py            continuous order and position monitor
  options_strategy.py   signal and contract selection
  risk.py               hard trading limits
web/                    interactive hosted demo
```

## Safety

AlphaBeater is experimental research software, not financial advice. Options can lose their full premium. Live trading is out of scope.

## References

- Tang, Z. et al. (2025). [*AlphaAgent: LLM-Driven Alpha Mining with Regularized Exploration to Counteract Alpha Decay*](https://arxiv.org/abs/2502.16789). arXiv:2502.16789.
- [Alpaca MCP Server](https://github.com/alpacahq/alpaca-mcp-server)

## License

MIT. See [LICENSE](LICENSE).
