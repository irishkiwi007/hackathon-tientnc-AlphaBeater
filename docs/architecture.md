# Architecture

## Workflow

```text
market snapshot + optional seed insight
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
       approve / revise / reject
                  |
        stock + options planner
                  |
             Risk Gate
                  |
       Alpaca paper execution + monitor
```

The model does not calculate backtest results or submit orders. Those steps are handled by regular code. An order must pass the evaluation and risk checks before it can reach Alpaca.

## Research data

Each run produces structured data:

- `MarketHypothesis` stores the proposed mechanism, direction, time horizon, evidence, and rejection criteria.
- `FactorCandidate` stores the factor expression, explanation, required inputs, time horizon, and expected direction.
- Later stages will add `FactorEvaluation`, `TradePlan`, `RiskDecision`, and `ExecutionRecord`.

Factor expressions are parsed but never passed to Python `eval`. Only registered operators and fields will be supported by the calculation engine.

## Model

`gemma-4-26b-a4b-it` is the default model. We can compare it with `gemma-4-31b-it` later. The pipeline uses a `StructuredLLM` interface, so the model can be changed without rewriting the agents.
