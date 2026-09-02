# AlphaBeater

AlphaBeater is an AI trading agent built for the Alpaca AI Trading Agents Hackathon. It uses market data to propose and test trading factors. Factors that pass evaluation can later be turned into stock or options trades in an Alpaca paper account.

In investing, alpha means return above a benchmark. The name AlphaBeater comes from the goal of finding useful alpha.

The project is still in its early stages. The current code does not submit paper or live orders.

## How it works

The planned workflow is:

1. The idea agent creates a market hypothesis from the available data.
2. The factor agent turns the hypothesis into factor expressions.
3. The evaluation engine backtests the factors and checks costs, turnover, and stability.
4. The strategy agent turns an accepted signal into a stock or options trade plan.
5. The risk gate approves, resizes, or rejects the plan.
6. Approved orders are sent to an Alpaca paper account and monitored.

The LLM proposes ideas and factor expressions. Regular Python code will calculate performance and enforce risk limits.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
copy .env.example .env  # use `cp` on macOS/Linux
pytest
```

The default model is `gemma-4-26b-a4b-it`. Set `GEMMA_MODEL` in `.env` to try `gemma-4-31b-it` or another compatible model. Do not commit `.env` or API keys.

After adding paper API keys to `.env`, check the connection with:

```bash
alphabeater-check
```

This command only reads account information. It does not place an order.

## Current repository layout

```text
src/alphabeater/
  agents/       hypothesis and factor proposal agents
  alpaca/       read-only paper account integration
  llm/          provider-neutral interface and Gemma adapter
  config.py     environment configuration
  dsl.py        safe factor-expression validation (never eval)
  models.py     typed research artifacts
  pipeline.py   research-loop orchestration
docs/
  architecture.md
tests/
```

## Near-term roadmap

- Alpaca historical stock/options data adapter and point-in-time snapshots
- Deterministic factor computation and leakage-safe walk-forward evaluation
- Candidate diversity/regularization and experiment memory
- Options-aware strategy construction and Greeks/liquidity filters
- Hard portfolio risk limits, kill switch, and Alpaca paper execution
- Audit dashboard, reproducible demo, and submission materials

## Safety

This is experimental research software, not financial advice. Live trading is out of scope.

## References

- Tang, Z. et al. (2025). [*AlphaAgent: LLM-Driven Alpha Mining with Regularized Exploration to Counteract Alpha Decay*](https://arxiv.org/abs/2502.16789). arXiv:2502.16789.

## License

See [LICENSE](LICENSE).
