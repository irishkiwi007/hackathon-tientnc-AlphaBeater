from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from alphabeater.backtest import BacktestMetrics
from alphabeater.models import Direction, FactorCandidate
from alphabeater.options_strategy import FactorSignal, OptionRight, OptionTradePlan
from alphabeater.risk import OptionsRiskGate, RiskContext


def plan(now: datetime, *, maximum_loss: Decimal = Decimal(400)) -> OptionTradePlan:
    candidate = FactorCandidate(
        name="momentum_signal",
        expression="returns(close, 5)",
        rationale="Tests whether recent momentum continues into the next holding period.",
        required_fields=["close"],
        horizon_days=5,
        expected_direction=Direction.POSITIVE,
    )
    signal = FactorSignal(
        underlying="SPY",
        raw_value=0.02,
        z_score=1.2,
        predicted_score=1.2,
        right=OptionRight.CALL,
        as_of=now - timedelta(days=1),
    )
    return OptionTradePlan(
        client_order_id="alphabeater-test",
        underlying="SPY",
        contract_symbol="SPY260925C00500000",
        right=OptionRight.CALL,
        expiration=date(2026, 9, 25),
        strike=Decimal(500),
        quantity=1,
        limit_price=maximum_loss / 100,
        maximum_loss=maximum_loss,
        bid_price=Decimal("3.90"),
        ask_price=Decimal("4.10"),
        relative_spread=Decimal("0.05"),
        delta=Decimal("0.50"),
        quote_timestamp=now - timedelta(seconds=30),
        factor_name=candidate.name,
        factor_expression=candidate.expression,
        signal=signal,
        rationale="A liquid, defined-risk paper options position from a validated signal.",
        created_at=now,
    )


def metrics() -> BacktestMetrics:
    return BacktestMetrics(
        observations=87,
        total_return=0.08,
        annualized_return=0.24,
        benchmark_return=0.07,
        excess_return=0.01,
        annualized_volatility=0.15,
        sharpe_ratio=1.2,
        max_drawdown=-0.07,
        win_rate=0.53,
        average_daily_turnover=0.2,
        estimated_cost=0.005,
        rebalance_days=20,
    )


def context() -> RiskContext:
    return RiskContext(
        account_status="ACTIVE",
        equity=Decimal(100000),
        last_equity=Decimal(100000),
        options_buying_power=Decimal(100000),
        options_trading_level=3,
        trading_blocked=False,
        current_options_exposure=Decimal(0),
        market_open=True,
    )


def test_approves_plan_when_every_hard_limit_passes() -> None:
    now = datetime(2026, 9, 2, 14, 31, tzinfo=UTC)
    decision = OptionsRiskGate().evaluate(plan(now), metrics(), context(), now=now)

    assert decision.approved
    assert all(check.passed for check in decision.checks)


def test_rejects_trade_that_risks_too_much() -> None:
    now = datetime(2026, 9, 2, 14, 31, tzinfo=UTC)
    decision = OptionsRiskGate().evaluate(
        plan(now, maximum_loss=Decimal(600)), metrics(), context(), now=now
    )

    assert not decision.approved
    assert "single-trade maximum loss" in decision.rejected_reasons


def test_experiment_keeps_failed_research_checks_advisory() -> None:
    now = datetime(2026, 9, 2, 14, 31, tzinfo=UTC)
    weak = metrics().model_copy(
        update={"sharpe_ratio": -0.2, "excess_return": -0.1}
    )

    decision = OptionsRiskGate().evaluate(
        plan(now),
        weak,
        context(),
        now=now,
        enforce_research=False,
    )

    assert decision.approved
    assert decision.rejected_reasons == []
    assert decision.advisory_reasons == ["holdout Sharpe", "holdout excess return"]
    assert all(
        not check.blocking
        for check in decision.checks
        if check.name in {"holdout Sharpe", "holdout excess return"}
    )
