# Architecture

## Workflow

```text
Alpaca market snapshot
                  |
             Idea Agent
                  |
          market hypothesis
                  |
            Factor Agent
                  |
       constrained DSL candidates
                  |
     deterministic evaluation engine
                  |
      rank by holdout evidence
                  |
       long-premium options planner
                  |
             Risk Gate
                  |
       official Alpaca MCP execution
                  |
        autonomous paper monitor
```

The model does not calculate backtest results or submit orders. Those steps are handled by regular code. An order must pass the evaluation and risk checks before it can reach Alpaca.

## Research data

Each run produces structured data:

- `MarketHypothesis` stores the proposed mechanism, direction, time horizon, evidence, and rejection criteria.
- `FactorCandidate` stores the factor expression, explanation, required inputs, time horizon, and expected direction.
- `BacktestResult` stores full-period and recent holdout metrics, including costs.
- `FactorSignal` stores the current standardized directional score.
- `OptionTradePlan` stores the selected OCC contract, quote, limit, and maximum loss.
- `RiskDecision` records every check, actual value, limit, and rejection reason.
- `PaperOrderReceipt` stores the Alpaca paper order response.
- `MonitorReport` stores order and position events.

Factor expressions are parsed but never passed to Python `eval`. Only registered operators and fields are supported by the calculation engine.

## Trading boundary

AlphaBeater only creates long calls and long puts. The options selector requires 21 to 45 days to expiry, 0.35 to 0.60 absolute delta, a positive two-sided quote, and at most a 20 percent relative spread. The order is a one-contract, buy-to-open, day limit order at the midpoint.

The risk gate is deterministic and runs after contract selection. Paper execution requires an explicit command-line flag, a current quote, an open market, positive holdout excess return, acceptable drawdown and Sharpe, sufficient option buying power, and all portfolio limits. It routes approved orders through Alpaca's official MCP `place_option_order` tool with paper mode forced on.

The monitor can run once or continuously. Automatic cancellations and sell-to-close exits remain disabled unless separately enabled in local configuration.

## Model

`gemma-4-26b-a4b-it` is the default model. We can compare it with `gemma-4-31b-it` later. The pipeline uses a `StructuredLLM` interface, so the model can be changed without rewriting the agents.
