"""Run the complete research-to-paper-order workflow."""

import argparse
import asyncio
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from alpaca.common.exceptions import APIError
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import QueryOrderStatus
from alpaca.trading.requests import GetOrdersRequest

from alphabeater.agents import FactorAgent, IdeaAgent
from alphabeater.alpaca import AlpacaMarketData, AlpacaPaperAccount
from alphabeater.backtest import BacktestMetrics, DevelopmentBacktestResult, FactorBacktester
from alphabeater.config import Settings
from alphabeater.factor_calculator import FactorCalculator
from alphabeater.llm import GemmaLLM
from alphabeater.mcp_execution import MCPPaperOrderExecutor
from alphabeater.models import FactorCandidate, MarketHypothesis, MarketObservation
from alphabeater.monitor import PaperPositionMonitor
from alphabeater.options_strategy import LongPremiumStrategy
from alphabeater.research_demo import _evidence, _to_frame
from alphabeater.risk import OptionsRiskGate, RiskContext

RESEARCH_THEMES = (
    "medium-term trend persistence and price strength",
    "short-term mean reversion after an unusually large move",
    "volatility-normalized direction and regime change",
    "volume confirmation or divergence from price",
    "breakout versus range-bound behavior using price location",
)


def _portfolio_context(client: TradingClient, plan_symbol: str) -> RiskContext:
    summary = AlpacaPaperAccount(client).get_summary()
    positions = client.get_all_positions()
    orders = client.get_orders(filter=GetOrdersRequest(status=QueryOrderStatus.OPEN))
    option_positions = [
        position
        for position in positions
        if getattr(position.asset_class, "value", str(position.asset_class)) == "us_option"
    ]
    exposure = sum(
        (abs(Decimal(str(position.cost_basis))) for position in option_positions),
        Decimal(0),
    )
    duplicate = any(position.symbol == plan_symbol for position in option_positions) or any(
        order.symbol == plan_symbol for order in orders
    )
    return RiskContext(
        account_status=summary.status,
        equity=summary.equity,
        last_equity=summary.last_equity,
        options_buying_power=summary.options_buying_power,
        options_trading_level=summary.options_trading_level,
        trading_blocked=summary.trading_blocked,
        current_options_exposure=exposure,
        market_open=bool(client.get_clock().is_open),
        duplicate_order_or_position=duplicate,
    )


def _best_candidate(
    results: list[tuple[int, FactorCandidate, DevelopmentBacktestResult]],
) -> tuple[int, FactorCandidate, DevelopmentBacktestResult]:
    if not results:
        raise ValueError("the factor agent returned no candidates")
    eligible = [item for item in results if _development_passes(item[2])]
    if not eligible:
        raise ValueError(
            "no candidate passed development validation; locked test was not evaluated"
        )
    return max(
        eligible,
        key=lambda item: (
            item[2].validation.sharpe_ratio,
            item[2].validation.excess_return,
            -abs(item[2].validation.max_drawdown),
        ),
    )


def _period_passes(metrics: BacktestMetrics, *, minimum_observations: int) -> bool:
    return (
        metrics.observations >= minimum_observations
        and metrics.sharpe_ratio >= 0.5
        and metrics.excess_return > 0
        and metrics.max_drawdown >= -0.15
    )


def _development_passes(result: DevelopmentBacktestResult) -> bool:
    return _period_passes(
        result.training, minimum_observations=100
    ) and _period_passes(result.validation, minimum_observations=40)


def _best_experimental_candidate(
    results: list[tuple[int, FactorCandidate, DevelopmentBacktestResult]],
) -> tuple[int, FactorCandidate, DevelopmentBacktestResult]:
    """Choose the least unstable candidate without claiming research approval."""
    return max(
        results,
        key=lambda item: (
            min(item[2].training.sharpe_ratio, item[2].validation.sharpe_ratio),
            min(item[2].training.excess_return, item[2].validation.excess_return),
            -max(
                abs(item[2].training.max_drawdown),
                abs(item[2].validation.max_drawdown),
            ),
        ),
    )


def run_workflow(
    *,
    execute: bool,
    output_path: Path,
    research_batches: int = 3,
    research_input: Path | None = None,
    paper_experiment: bool = False,
) -> dict[str, Any]:
    if not 1 <= research_batches <= 5:
        raise ValueError("research_batches must be between 1 and 5")
    settings = Settings()
    now = datetime.now(UTC)
    api_key, secret_key = settings.require_alpaca_credentials()
    market_data = AlpacaMarketData.from_settings(settings)
    bars = market_data.get_daily_bars(
        ["SPY", "QQQ", "IWM"], start=now - timedelta(days=420), end=now
    )
    frame = _to_frame(bars)
    observation = MarketObservation(
        as_of=max(bar.timestamp for bar in bars).isoformat(),
        universe=["SPY", "QQQ", "IWM"],
        evidence=_evidence(frame),
    )
    calculator = FactorCalculator()
    backtester = FactorBacktester()
    hypotheses: list[MarketHypothesis] = []
    evaluated: list[tuple[int, FactorCandidate, DevelopmentBacktestResult]] = []
    if research_input is not None:
        saved = json.loads(research_input.read_text(encoding="utf-8"))
        hypotheses = [MarketHypothesis.model_validate(item) for item in saved["hypotheses"]]
        for item in saved["candidates"]:
            candidate = FactorCandidate.model_validate(
                {name: item[name] for name in FactorCandidate.model_fields}
            )
            calculator.calculate(frame, candidate.expression)
            evaluated.append(
                (
                    int(item["research_batch"]),
                    candidate,
                    backtester.run_development(
                        frame, candidate.expression, candidate.expected_direction
                    ),
                )
            )
        research_batches = len(hypotheses)
    else:
        llm = GemmaLLM(api_key=settings.require_gemini_key(), model=settings.gemma_model)
        for batch in range(1, research_batches + 1):
            theme = RESEARCH_THEMES[batch - 1]
            hypothesis = IdeaAgent(llm).propose(
                observation,
                seed_insight=(
                    f"Independent precommitted research batch {batch} of {research_batches}. "
                    f"Focus on {theme}."
                ),
            )
            hypotheses.append(hypothesis)
            factors = FactorAgent(llm).propose(
                hypothesis,
                execution_check=lambda expression: calculator.calculate(frame, expression),
            )
            evaluated.extend(
                (
                    batch,
                    factor,
                    backtester.run_development(
                        frame, factor.expression, factor.expected_direction
                    ),
                )
                for factor in factors.candidates
            )
    candidate_records = [
        {
            **item_candidate.model_dump(mode="json"),
            "research_batch": item_batch,
            "development_backtest": item_backtest.model_dump(mode="json"),
            "development_eligible": _development_passes(item_backtest),
            "selected": False,
        }
        for item_batch, item_candidate, item_backtest in evaluated
    ]
    has_eligible_candidate = any(item["development_eligible"] for item in candidate_records)
    if not has_eligible_candidate and not paper_experiment:
        output = {
            "run_at": now.isoformat(),
            "mode": "paper",
            "execution_requested": execute,
            "status": "abstained_before_locked_test",
            "reason": "no candidate passed both training and validation gates",
            "research_protocol": {
                "generator_model": settings.gemma_model,
                "trained_predictive_model": None,
                "candidate_count": len(evaluated),
                "research_batches": research_batches,
                "research_source": (
                    str(research_input)
                    if research_input is not None
                    else "new Gemma generation"
                ),
                "selection_data": "training eligibility and validation ranking",
                "locked_test_evaluated": False,
                "transaction_cost_bps": 5,
            },
            "observation": observation.model_dump(mode="json"),
            "hypothesis": None,
            "hypotheses": [item.model_dump(mode="json") for item in hypotheses],
            "candidates": candidate_records,
            "selected_backtest": None,
            "trade_plan": None,
            "risk": None,
            "order": None,
            "monitor": None,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        return output
    if has_eligible_candidate:
        selected_batch, candidate, _ = _best_candidate(evaluated)
    else:
        selected_batch, candidate, _ = _best_experimental_candidate(evaluated)
    hypothesis = hypotheses[selected_batch - 1]
    # Candidate selection is complete before the locked holdout is evaluated.
    backtest = backtester.run(frame, candidate.expression, candidate.expected_direction)

    strategy = LongPremiumStrategy()
    trading_client = TradingClient(api_key, secret_key, paper=True)
    account = AlpacaPaperAccount(trading_client).get_summary()
    risk_gate = OptionsRiskGate()
    maximum_loss_budget = min(
        account.equity * risk_gate.policy.max_trade_risk_pct,
        account.options_buying_power,
    )
    plan = None
    plan_errors = []
    for signal in strategy.derive_signals(frame, candidate):
        latest_close = Decimal(
            str(
                frame.loc[frame["symbol"] == signal.underlying]
                .sort_values("timestamp")
                .iloc[-1]["close"]
            )
        )
        quotes = market_data.get_option_chain(
            signal.underlying,
            expiration_start=(now + timedelta(days=21)).date(),
            expiration_end=(now + timedelta(days=45)).date(),
            strike_min=latest_close * Decimal("0.88"),
            strike_max=latest_close * Decimal("1.12"),
        )
        try:
            plan = strategy.build_plan(
                signal,
                candidate,
                quotes,
                maximum_loss_budget=maximum_loss_budget,
                now=now,
            )
            break
        except ValueError as exc:
            plan_errors.append(f"{signal.underlying}: {exc}")
    if plan is None:
        raise ValueError("; ".join(plan_errors))

    context = _portfolio_context(trading_client, plan.contract_symbol)
    decision = risk_gate.evaluate(
        plan,
        backtest.holdout,
        context,
        now=now,
        require_market_open=execute,
        enforce_research=not paper_experiment,
    )
    receipt = None
    if execute and decision.approved:
        receipt = asyncio.run(
            MCPPaperOrderExecutor(settings, execution_enabled=True).submit(plan, decision)
        )

    monitor = PaperPositionMonitor(
        trading_client,
        automatic_exits=settings.enable_automatic_exits,
    ).check_once(now=now)
    output: dict[str, Any] = {
        "run_at": now.isoformat(),
        "mode": "paper",
        "execution_policy": (
            "experimental_forward_paper" if paper_experiment else "research_validated"
        ),
        "research_qualified": has_eligible_candidate,
        "execution_requested": execute,
        "mcp_execution": True,
        "research_protocol": {
            "generator_model": settings.gemma_model,
            "trained_predictive_model": None,
            "candidate_count": len(evaluated),
            "research_batches": research_batches,
            "research_source": (
                str(research_input) if research_input is not None else "new Gemma generation"
            ),
            "selection_data": "validation only",
            "development_gate": {
                "applies_to": "both training and validation",
                "minimum_training_observations": 100,
                "minimum_validation_observations": 40,
                "minimum_sharpe": 0.5,
                "minimum_excess_return": 0,
                "maximum_drawdown": -0.15,
            },
            "final_evaluation": "one locked chronological holdout for the selected candidate",
            "transaction_cost_bps": 5,
        },
        "observation": observation.model_dump(mode="json"),
        "hypothesis": hypothesis.model_dump(mode="json"),
        "hypotheses": [item.model_dump(mode="json") for item in hypotheses],
        "candidates": [
            {
                **item_candidate.model_dump(mode="json"),
                "research_batch": item_batch,
                "development_backtest": item_backtest.model_dump(mode="json"),
                "development_eligible": _development_passes(item_backtest),
                "selected": (
                    item_batch == selected_batch and item_candidate.name == candidate.name
                ),
            }
            for item_batch, item_candidate, item_backtest in evaluated
        ],
        "selected_backtest": backtest.model_dump(mode="json"),
        "trade_plan": plan.model_dump(mode="json"),
        "risk": decision.model_dump(mode="json"),
        "order": None if receipt is None else receipt.model_dump(mode="json"),
        "monitor": monitor.model_dump(mode="json"),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full AlphaBeater paper workflow")
    parser.add_argument(
        "--paper-experiment",
        action="store_true",
        help=(
            "allow an explicitly unvalidated paper trade while keeping operational and "
            "financial risk checks blocking"
        ),
    )
    parser.add_argument(
        "--reuse-research",
        type=Path,
        help="reuse hypotheses and candidates from an earlier audit artifact",
    )
    parser.add_argument(
        "--research-batches",
        type=int,
        default=3,
        choices=range(1, 6),
        metavar="1-5",
        help="precommitted independent Gemma batches before validation selection",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="submit an approved paper order through Alpaca MCP",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/latest-run.json"),
        help="where to save the complete audit record",
    )
    args = parser.parse_args()
    try:
        output = run_workflow(
            execute=args.execute,
            output_path=args.output,
            research_batches=args.research_batches,
            research_input=args.reuse_research,
            paper_experiment=args.paper_experiment,
        )
    except (APIError, OSError, RuntimeError, ValueError) as exc:
        print(f"AlphaBeater run failed: {exc}")
        return 1
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
