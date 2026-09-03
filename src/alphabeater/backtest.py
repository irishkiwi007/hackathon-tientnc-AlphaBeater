"""Simple leakage-aware backtesting for generated factors."""

import math

import pandas as pd
from pydantic import BaseModel, ConfigDict

from alphabeater.factor_calculator import FactorCalculator
from alphabeater.models import Direction


class BacktestMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observations: int
    total_return: float
    annualized_return: float
    benchmark_return: float
    excess_return: float
    annualized_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    average_daily_turnover: float
    estimated_cost: float
    rebalance_days: int


class BacktestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    holdout_start: str
    holdout_end: str
    full_period: BacktestMetrics
    holdout: BacktestMetrics


class FactorBacktester:
    def __init__(self, *, transaction_cost_bps: float = 5.0, test_fraction: float = 0.3) -> None:
        if transaction_cost_bps < 0:
            raise ValueError("transaction_cost_bps cannot be negative")
        if not 0.1 <= test_fraction <= 0.5:
            raise ValueError("test_fraction must be between 0.1 and 0.5")
        self._cost_rate = transaction_cost_bps / 10_000
        self._test_fraction = test_fraction

    def run(
        self,
        frame: pd.DataFrame,
        expression: str,
        direction: Direction,
    ) -> BacktestResult:
        ordered = frame.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
        factor = FactorCalculator().calculate(ordered, expression)
        factor_frame = ordered[["symbol", "timestamp"]].copy()
        factor_frame["factor"] = factor

        close = ordered.pivot(index="timestamp", columns="symbol", values="close").sort_index()
        scores = factor_frame.pivot(index="timestamp", columns="symbol", values="factor")
        scores = scores.reindex(close.index)
        if direction == Direction.NEGATIVE:
            scores = -scores

        winners = scores.eq(scores.max(axis=1), axis=0) & scores.notna()
        weights = winners.div(winners.sum(axis=1).replace(0, float("nan")), axis=0).fillna(0)
        held_weights = weights.shift(1).fillna(0)
        asset_returns = close.pct_change(fill_method=None)
        gross_returns = (held_weights * asset_returns).sum(axis=1, min_count=1).fillna(0)
        turnover = held_weights.diff().fillna(held_weights).abs().sum(axis=1)
        costs = turnover * self._cost_rate
        net_returns = gross_returns - costs
        benchmark = asset_returns.mean(axis=1).fillna(0)

        split = max(1, int(len(net_returns) * (1 - self._test_fraction)))
        test_returns = net_returns.iloc[split:]
        test_benchmark = benchmark.iloc[split:]
        test_turnover = turnover.iloc[split:]
        test_costs = costs.iloc[split:]
        if test_returns.empty:
            raise ValueError("not enough observations for an out-of-sample period")

        return BacktestResult(
            holdout_start=test_returns.index[0].isoformat(),
            holdout_end=test_returns.index[-1].isoformat(),
            full_period=self._metrics(net_returns, benchmark, turnover, costs),
            holdout=self._metrics(
                test_returns,
                test_benchmark,
                test_turnover,
                test_costs,
            ),
        )

    @staticmethod
    def _metrics(
        returns: pd.Series,
        benchmark: pd.Series,
        turnover: pd.Series,
        costs: pd.Series,
    ) -> BacktestMetrics:
        observations = len(returns)
        total_return = float((1 + returns).prod() - 1)
        benchmark_return = float((1 + benchmark).prod() - 1)
        annualized_return = float((1 + total_return) ** (252 / observations) - 1)
        volatility = float(returns.std(ddof=1) * math.sqrt(252))
        sharpe = 0.0
        if returns.std(ddof=1) > 0:
            sharpe = float(returns.mean() / returns.std(ddof=1) * math.sqrt(252))
        equity = (1 + returns).cumprod()
        drawdown = equity / equity.cummax() - 1
        return BacktestMetrics(
            observations=observations,
            total_return=total_return,
            annualized_return=annualized_return,
            benchmark_return=benchmark_return,
            excess_return=total_return - benchmark_return,
            annualized_volatility=volatility,
            sharpe_ratio=sharpe,
            max_drawdown=float(drawdown.min()),
            win_rate=float((returns > 0).mean()),
            average_daily_turnover=float(turnover.mean()),
            estimated_cost=float(costs.sum()),
            rebalance_days=int((turnover > 0).sum()),
        )
