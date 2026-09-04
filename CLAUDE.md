# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AlphaBeater is an LLM-driven alpha-mining agent for the Alpaca AI Trading Agents Hackathon. An LLM proposes market hypotheses and factor expressions; deterministic Python is meant to backtest them, size trades, and enforce risk limits. Only the first two stages (idea → factor) exist today. See `docs/architecture.md` for the full intended pipeline and `README.md` for the roadmap.

Design inspiration: [AlphaAgent (arXiv:2502.16789)](https://arxiv.org/abs/2502.16789).

## Commands

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; source .venv/bin/activate elsewhere
pip install -e ".[dev]"

pytest                          # full suite (testpaths = tests/)
pytest tests/test_dsl.py::test_valid_expressions          # single test
pytest tests/test_dsl.py -k "unregistered"                # by name
ruff check .                    # lint (line-length 100, py311)
ruff format .
```

Tests use a `FakeLLM` stub and require no API keys or network access. `GEMINI_API_KEY` is only needed to actually call `GemmaLLM`.

## Architecture

The load-bearing invariant is the **trust boundary between LLM output and executable behavior**. Every layer exists to enforce it, so changes that weaken it are the ones that matter:

1. **`llm/base.py` — `StructuredLLM` Protocol.** Agents depend on this structural type only, never on a concrete provider. That is why tests can inject a plain class with a `generate` method. Keep new providers conforming to it rather than adding provider branches inside agents.
2. **`llm/gemma.py` — `GemmaLLM`.** Serializes the target Pydantic model's JSON Schema into the prompt, then re-validates the reply through `model_validate`. Raw model text is never returned; malformed JSON or schema violations raise `ValueError`.
3. **`models.py` — typed artifacts.** All inherit `StrictModel` (`extra="forbid"`) with tight `Field` constraints (regex names, length and range bounds). These constraints are the *primary* defense against model drift — they are validation, not documentation. Later stages will add `FactorEvaluation`, `TradePlan`, `RiskDecision`, `ExecutionRecord`.
4. **`dsl.py` — factor language.** Expressions are parsed with `ast.parse(mode="eval")` and walked; anything outside `ALLOWED_FIELDS` / `ALLOWED_OPERATORS`, non-numeric constants, keyword arguments, or unlisted AST node types is rejected. **Never call `eval`/`exec` on a factor expression.** A future evaluation engine must interpret the AST against a registered operator table. Adding an operator means editing `ALLOWED_OPERATORS` *and* implementing it in that table — the two must stay in sync.
5. **`agents/`** — thin prompt-construction wrappers. `IdeaAgent` produces a `MarketHypothesis` from a `MarketObservation`; `FactorAgent` produces a `FactorProposal` and then re-checks each candidate through `validate_expression` plus a `required_fields` subset check. Agent-side validation is deliberately redundant with Pydantic — keep it.
6. **`pipeline.py` — `ResearchPipeline`.** Takes both agents by constructor injection and returns a `ResearchBundle`.

## Conventions

- Absolute imports (`from alphabeater.dsl import ...`) throughout; src layout under `src/alphabeater`.
- Dependencies are injected via constructors, never constructed inside agents — this is what keeps the suite network-free.
- Prompts instruct the model to produce mechanisms and expressions but **never** performance claims or statistics; backtest numbers come from code only.
- `config.py` guards: `require_gemini_key()` and `assert_paper_trading()`. Live trading is out of scope — `alpaca_paper` must stay true.
- Optional runtime deps (`google.genai`) are imported lazily inside `__init__` so the package imports without them.

## Scope boundary

The repo submits no orders and has no Alpaca adapter yet. When adding execution, keep the ordering from `docs/architecture.md`: evaluation → risk gate → paper execution. Nothing reaches Alpaca without passing both gates.
