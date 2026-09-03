from datetime import UTC, datetime, timedelta

import pandas as pd

from alphabeater.backtest import FactorBacktester
from alphabeater.models import Direction


def trending_market_frame() -> pd.DataFrame:
    rows = []
    start = datetime(2025, 1, 1, tzinfo=UTC)
    for symbol, daily_change in [("SPY", 1.0), ("QQQ", 0.5), ("IWM", -0.2)]:
        for day in range(100):
            close = 100 + daily_change * day
            rows.append(
                {
                    "symbol": symbol,
                    "timestamp": start + timedelta(days=day),
                    "open": close - 0.2,
                    "high": close + 0.5,
                    "low": close - 0.5,
                    "close": close,
                    "volume": 1_000 + day,
                    "vwap": close,
                }
            )
    return pd.DataFrame(rows)


def test_backtest_uses_next_period_returns_and_reports_holdout() -> None:
    result = FactorBacktester(transaction_cost_bps=0).run(
        trending_market_frame(),
        "returns(close, 5)",
        Direction.POSITIVE,
    )

    assert result.holdout.observations == 30
    assert result.holdout.total_return > 0
    assert result.holdout.excess_return > 0
    assert result.holdout_start < result.holdout_end


def test_transaction_costs_reduce_returns() -> None:
    frame = trending_market_frame()
    without_cost = FactorBacktester(transaction_cost_bps=0).run(
        frame, "returns(close, 5)", Direction.POSITIVE
    )
    with_cost = FactorBacktester(transaction_cost_bps=10).run(
        frame, "returns(close, 5)", Direction.POSITIVE
    )

    assert with_cost.full_period.total_return < without_cost.full_period.total_return
