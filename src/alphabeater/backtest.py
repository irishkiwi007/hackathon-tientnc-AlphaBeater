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


class DevelopmentBacktestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    training_start: str
    training_end: str
    validation_start: str
    validation_end: str
    training: BacktestMetrics
    validation: BacktestMetrics


class BacktestResult(DevelopmentBacktestResult):
    holdout_start: str
    holdout_end: str
    full_period: BacktestMetrics
    holdout: BacktestMetrics


class FactorBacktester:
    def __init__(
        self,
        *,
        transaction_cost_bps: float = 5.0,
        validation_fraction: float = 0.2,
        test_fraction: float = 0.3,
        signal_lookback: int = 60,
    ) -> None:
        if transaction_cost_bps < 0:
            raise ValueError("transaction_cost_bps cannot be negative")
        if not 0.1 <= test_fraction <= 0.5:
            raise ValueError("test_fraction must be between 0.1 and 0.5")
        if not 0.1 <= validation_fraction <= 0.4:
            raise ValueError("validation_fraction must be between 0.1 and 0.4")
        if validation_fraction + test_fraction > 0.7:
            raise ValueError("training period must contain at least 30 percent of observations")
        self._cost_rate = transaction_cost_bps / 10_000
        self._validation_fraction = validation_fraction
        self._test_fraction = test_fraction
        self._signal_lookback = signal_lookback

    def run_development(
        self,
        frame: pd.DataFrame,
        expression: str,
        direction: Direction,
    ) -> DevelopmentBacktestResult:
        net_returns, benchmark, turnover, costs = self._return_series(frame, expression, direction)
        train_end, validation_end = self._split_points(len(net_returns))
        return DevelopmentBacktestResult(
            training_start=net_returns.index[0].isoformat(),
            training_end=net_returns.index[train_end - 1].isoformat(),
            validation_start=net_returns.index[train_end].isoformat(),
            validation_end=net_returns.index[validation_end - 1].isoformat(),
            training=self._metrics_for_slice(
                net_returns, benchmark, turnover, costs, slice(0, train_end)
            ),
            validation=self._metrics_for_slice(
                net_returns, benchmark, turnover, costs, slice(train_end, validation_end)
            ),
        )

    def run(
        self,
        frame: pd.DataFrame,
        expression: str,
        direction: Direction,
    ) -> BacktestResult:
        net_returns, benchmark, turnover, costs = self._return_series(frame, expression, direction)
        _, validation_end = self._split_points(len(net_returns))
        development = self.run_development(frame, expression, direction)
        test_returns = net_returns.iloc[validation_end:]
        if test_returns.empty:
            raise ValueError("not enough observations for a locked test period")

        return BacktestResult(
            **development.model_dump(),
            holdout_start=test_returns.index[0].isoformat(),
            holdout_end=test_returns.index[-1].isoformat(),
            full_period=self._metrics(net_returns, benchmark, turnover, costs),
            holdout=self._metrics_for_slice(
                net_returns, benchmark, turnover, costs, slice(validation_end, None)
            ),
        )

    def _return_series(
        self,
        frame: pd.DataFrame,
        expression: str,
        direction: Direction,
    ) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        ordered = frame.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
        factor = FactorCalculator().calculate(ordered, expression)
        factor_frame = ordered[["symbol", "timestamp"]].copy()
        factor_frame["factor"] = factor

        close = ordered.pivot(index="timestamp", columns="symbol", values="close").sort_index()
        scores = factor_frame.pivot(index="timestamp", columns="symbol", values="factor")
        scores = scores.reindex(close.index)
        if direction == Direction.NEGATIVE:
            scores = -scores

        rolling_mean = scores.rolling(self._signal_lookback, min_periods=10).mean()
        rolling_std = scores.rolling(self._signal_lookback, min_periods=10).std(ddof=1)
        standardized = (scores - rolling_mean) / rolling_std.replace(0, float("nan"))
        strongest = standardized.abs().max(axis=1)
        winners = standardized.abs().eq(strongest, axis=0) & standardized.notna()
        signs = standardized.gt(0).astype(float) - standardized.lt(0).astype(float)
        weights = (
            (winners * signs).div(winners.sum(axis=1).replace(0, float("nan")), axis=0).fillna(0)
        )
        held_weights = weights.shift(1).fillna(0)
        asset_returns = close.pct_change(fill_method=None)
        gross_returns = (held_weights * asset_returns).sum(axis=1, min_count=1).fillna(0)
        turnover = held_weights.diff().fillna(held_weights).abs().sum(axis=1)
        costs = turnover * self._cost_rate
        net_returns = gross_returns - costs
        benchmark = asset_returns.mean(axis=1).fillna(0)

        if len(net_returns) < 10:
            raise ValueError("not enough observations for train, validation, and test periods")
        return net_returns, benchmark, turnover, costs

    def _split_points(self, observations: int) -> tuple[int, int]:
        train_end = max(
            1, int(observations * (1 - self._validation_fraction - self._test_fraction))
        )
        validation_end = max(train_end + 1, int(observations * (1 - self._test_fraction)))
        if validation_end >= observations:
            raise ValueError("not enough observations for train, validation, and test periods")
        return train_end, validation_end

    def _metrics_for_slice(
        self,
        returns: pd.Series,
        benchmark: pd.Series,
        turnover: pd.Series,
        costs: pd.Series,
        period: slice,
    ) -> BacktestMetrics:
        return self._metrics(
            returns.iloc[period],
            benchmark.iloc[period],
            turnover.iloc[period],
            costs.iloc[period],
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
