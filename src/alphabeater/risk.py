"""Deterministic risk policy for proposed options trades."""

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from alphabeater.backtest import BacktestMetrics
from alphabeater.options_strategy import OptionTradePlan


class RiskPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_trade_risk_pct: Decimal = Decimal("0.005")
    max_total_options_exposure_pct: Decimal = Decimal("0.02")
    max_daily_loss_pct: Decimal = Decimal("0.02")
    max_contracts: int = 1
    max_relative_spread: Decimal = Decimal("0.20")
    max_quote_age_seconds: int = 900
    min_holdout_observations: int = 60
    min_holdout_sharpe: float = 0.5
    min_holdout_excess_return: float = 0.0
    max_holdout_drawdown: float = 0.15


class RiskContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_status: str
    equity: Decimal = Field(gt=0)
    last_equity: Decimal = Field(gt=0)
    options_buying_power: Decimal = Field(ge=0)
    options_trading_level: int = Field(ge=0)
    trading_blocked: bool
    current_options_exposure: Decimal = Field(ge=0)
    market_open: bool
    duplicate_order_or_position: bool = False


class RiskCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    passed: bool
    actual: str
    limit: str


class RiskDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool
    max_allowed_trade_loss: Decimal
    projected_options_exposure: Decimal
    checks: list[RiskCheck]
    rejected_reasons: list[str]
    evaluated_at: datetime


class OptionsRiskGate:
    def __init__(self, policy: RiskPolicy | None = None) -> None:
        self.policy = policy or RiskPolicy()

    def evaluate(
        self,
        plan: OptionTradePlan,
        backtest: BacktestMetrics,
        context: RiskContext,
        *,
        now: datetime | None = None,
        require_market_open: bool = True,
    ) -> RiskDecision:
        evaluated_at = now or datetime.now(UTC)
        quote_time = plan.quote_timestamp
        if quote_time.tzinfo is None:
            quote_time = quote_time.replace(tzinfo=UTC)
        quote_age = max(0.0, (evaluated_at - quote_time).total_seconds())
        daily_loss = max(Decimal(0), context.last_equity - context.equity)
        daily_loss_pct = daily_loss / context.last_equity
        max_trade_loss = context.equity * self.policy.max_trade_risk_pct
        projected_exposure = context.current_options_exposure + plan.maximum_loss
        maximum_exposure = context.equity * self.policy.max_total_options_exposure_pct

        raw_checks = [
            (
                "paper account active",
                "ACTIVE" in context.account_status.upper(),
                context.account_status,
                "ACTIVE",
            ),
            ("trading enabled", not context.trading_blocked, str(context.trading_blocked), "false"),
            (
                "options permission",
                context.options_trading_level >= 2,
                str(context.options_trading_level),
                ">= 2",
            ),
            (
                "market open",
                context.market_open or not require_market_open,
                f"{context.market_open} ({'execution' if require_market_open else 'preview'})",
                "true when executing",
            ),
            (
                "no duplicate exposure",
                not context.duplicate_order_or_position,
                str(context.duplicate_order_or_position),
                "false",
            ),
            (
                "contract quantity",
                plan.quantity <= self.policy.max_contracts,
                str(plan.quantity),
                f"<= {self.policy.max_contracts}",
            ),
            (
                "single-trade maximum loss",
                plan.maximum_loss <= max_trade_loss,
                f"${plan.maximum_loss:.2f}",
                f"<= ${max_trade_loss:.2f}",
            ),
            (
                "portfolio options exposure",
                projected_exposure <= maximum_exposure,
                f"${projected_exposure:.2f}",
                f"<= ${maximum_exposure:.2f}",
            ),
            (
                "options buying power",
                plan.maximum_loss <= context.options_buying_power,
                f"${plan.maximum_loss:.2f}",
                f"<= ${context.options_buying_power:.2f}",
            ),
            (
                "daily loss kill switch",
                daily_loss_pct < self.policy.max_daily_loss_pct,
                f"{daily_loss_pct:.2%}",
                f"< {self.policy.max_daily_loss_pct:.2%}",
            ),
            (
                "quote freshness",
                quote_age <= self.policy.max_quote_age_seconds,
                f"{quote_age:.0f}s",
                f"<= {self.policy.max_quote_age_seconds}s",
            ),
            (
                "bid-ask spread",
                plan.relative_spread <= self.policy.max_relative_spread,
                f"{plan.relative_spread:.1%}",
                f"<= {self.policy.max_relative_spread:.1%}",
            ),
            (
                "holdout sample",
                backtest.observations >= self.policy.min_holdout_observations,
                str(backtest.observations),
                f">= {self.policy.min_holdout_observations}",
            ),
            (
                "holdout Sharpe",
                backtest.sharpe_ratio >= self.policy.min_holdout_sharpe,
                f"{backtest.sharpe_ratio:.2f}",
                f">= {self.policy.min_holdout_sharpe:.2f}",
            ),
            (
                "holdout excess return",
                backtest.excess_return > self.policy.min_holdout_excess_return,
                f"{backtest.excess_return:.2%}",
                f"> {self.policy.min_holdout_excess_return:.2%}",
            ),
            (
                "holdout drawdown",
                backtest.max_drawdown >= -self.policy.max_holdout_drawdown,
                f"{backtest.max_drawdown:.2%}",
                f">= {-self.policy.max_holdout_drawdown:.2%}",
            ),
        ]
        checks = [
            RiskCheck(name=name, passed=passed, actual=actual, limit=limit)
            for name, passed, actual, limit in raw_checks
        ]
        rejected = [check.name for check in checks if not check.passed]
        return RiskDecision(
            approved=not rejected,
            max_allowed_trade_loss=max_trade_loss,
            projected_options_exposure=projected_exposure,
            checks=checks,
            rejected_reasons=rejected,
            evaluated_at=evaluated_at,
        )
