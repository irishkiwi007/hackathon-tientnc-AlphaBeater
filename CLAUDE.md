# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AlphaBeater is an autonomous, risk-gated options agent for the Alpaca AI Trading Agents Hackathon.
Gemma forms a market hypothesis and proposes factor expressions in a small DSL; deterministic Python
calculates those factors, backtests them, selects an option contract, enforces every trading limit,
and routes an approved paper order through Alpaca's official MCP server.

The complete pipeline exists and runs end to end. `README.md` documents the workflow stage by stage;
`docs/architecture.md` covers the intended design.

Design inspiration: [AlphaAgent (arXiv:2502.16789)](https://arxiv.org/abs/2502.16789).

## Commands

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; source .venv/bin/activate elsewhere
pip install -e ".[dev]"

pytest                          # full suite (testpaths = tests/)
pytest tests/test_risk.py -k "spread"                     # by name
ruff check src tests            # lint (line-length 100, py311)
ruff format src tests
```

Entry points (`pyproject.toml` `[project.scripts]`):

| Command | Purpose |
| --- | --- |
| `alphabeater-check` | paper account and Gemma configuration |
| `alphabeater-data-check` | Alpaca IEX bars and indicative option chain |
| `alphabeater-mcp-check` | official Alpaca MCP server connection (`--describe` lists tool schemas) |
| `alphabeater-research-demo` | hypothesis, factor calculation, backtest |
| `alphabeater-run` | the complete workflow; preview only unless `--execute` |
| `alphabeater-monitor` | order and position monitor (`--watch`) |

Tests use stubs and require no API keys or network access. `.env` supplies `GEMINI_API_KEY`,
`GEMMA_MODEL`, and the Alpaca paper credentials.

## Architecture

The load-bearing invariant is the **trust boundary between LLM output and executable behavior**.
The LLM does research; Python calculates every number and makes every trading decision. Changes that
weaken that separation are the ones that matter.

1. **`llm/base.py` — `StructuredLLM` Protocol.** Agents depend on this structural type only, never on
   a concrete provider. That is why tests inject a plain class with a `generate` method, and why a
   second provider drops in without touching agent code. Keep new providers conforming to it rather
   than adding provider branches inside agents.
2. **`llm/gemma.py` — `GemmaLLM`.** Serializes the target Pydantic model's JSON Schema into the
   prompt, then re-validates the reply through `model_validate`. Raw model text is never returned;
   malformed JSON or schema violations raise `ValueError`.
3. **`models.py` — typed artifacts.** All inherit `StrictModel` (`extra="forbid"`) with tight `Field`
   constraints. These constraints are the *primary* defense against model drift — validation, not
   documentation.
4. **`dsl.py` — factor language.** Expressions are parsed with `ast.parse(mode="eval")` and walked;
   anything outside `ALLOWED_FIELDS` (6 bar fields) or `ALLOWED_OPERATORS` (15 operators), non-numeric
   constants, keyword arguments, or unlisted AST node types is rejected.
   **Never call `eval`/`exec` on a factor expression.**
5. **`factor_calculator.py` — the interpreter.** Walks the validated AST against a registered operator
   table over a pandas frame. Adding a DSL operator means editing `ALLOWED_OPERATORS` *and*
   implementing it here — the two must stay in sync or validation will accept an expression nothing
   can compute.
6. **`backtest.py` — leakage-safe evaluation.** Chronological 50/20/30 split: training checks
   consistency, validation ranks and selects, the final 30% is a locked test evaluated once after
   selection. Never feed test results back into selection; never re-run the locked period hunting for
   a pass.
7. **`options_strategy.py` — `LongPremiumStrategy`.** Turns a standardized signal into a long call or
   put, then searches the chain for 21–45 DTE and 0.35–0.60 absolute delta within the risk budget.
   Long premium only — maximum loss is the premium paid, never naked short.
8. **`risk.py` — `OptionsRiskGate`.** The hard limits live in `RiskPolicy` (0.5% max trade risk, 2%
   total options exposure, 2% daily loss kill switch, 1 contract, 20% max spread, 900s max quote age,
   plus holdout thresholds). **The LLM cannot reach this policy.** Every rejection returns a reason
   code.
9. **`alpaca/`** — `account.py` and `market_data.py` adapters.
10. **`execution.py` / `mcp_execution.py`** — SDK and MCP order adapters. `agent_run.py` uses the MCP
    path. Orders carry deterministic client order IDs so a retry cannot silently open a second
    position.
11. **`monitor.py` — `PaperPositionMonitor`.** Stale-entry, stop-loss, take-profit and DTE rules;
    appends to `artifacts/trading-journal.jsonl`. Only acts when `ENABLE_AUTOMATIC_EXITS=true`.
12. **`agent_run.py`** — wires the whole workflow and writes the audit record to
    `artifacts/latest-run.json`.
13. **`web/`** — Next.js dashboard deployed on Vercel.

## Conventions

- Absolute imports (`from alphabeater.dsl import ...`); src layout under `src/alphabeater`.
- Dependencies are injected via constructors, never constructed inside agents — this is what keeps
  the suite network-free.
- Prompts instruct the model to produce mechanisms and expressions but **never** performance claims
  or statistics; every number comes from code.
- `config.py` guards: `require_gemini_key()`, `assert_paper_trading()`, `require_alpaca_credentials()`.
- Optional runtime deps are imported lazily so the package imports without them.
- `artifacts/` is gitignored — generated records may contain account or order details. Sanitize
  before committing anything from it.

## Safety boundary

Paper trading only. `alpaca_paper` must stay true, and `assert_paper_trading()` runs before any
executor is constructed. Two switches, both defaulting to false, gate autonomous behavior:
`ENABLE_PAPER_ORDERS` and `ENABLE_AUTOMATIC_EXITS`. Neither can enable live trading.

`alphabeater-run` cannot submit anything without an explicit `--execute`, and even then only if every
risk check passes. `--paper-experiment` relaxes the *research* gate only; the account, market-hours,
exposure, liquidity and loss checks stay blocking, and the audit labels the run
`experimental_forward_paper`.
