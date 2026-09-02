from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from alphabeater.factor_calculator import FactorCalculationError, FactorCalculator


def market_frame() -> pd.DataFrame:
    rows = []
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for symbol, offset in [("SPY", 0), ("QQQ", 20)]:
        for day in range(30):
            price = 100 + offset + day
            rows.append(
                {
                    "symbol": symbol,
                    "timestamp": start + timedelta(days=day),
                    "open": price - 1,
                    "high": price + 1,
                    "low": price - 2,
                    "close": price,
                    "volume": 1_000 + 10 * day,
                    "vwap": price - 0.25,
                }
            )
    return pd.DataFrame(rows)


def test_calculates_nested_factor() -> None:
    result = FactorCalculator().calculate(
        market_frame(),
        "mul(returns(close, 5), relative_volume(volume, 20))",
    )

    assert result.notna().sum() == 22


def test_calculates_cross_sectional_rank() -> None:
    result = FactorCalculator().calculate(market_frame(), "rank(returns(close, 5))")

    assert result.dropna().between(0, 1).all()


def test_rejects_window_that_cannot_run() -> None:
    with pytest.raises(FactorCalculationError, match="window"):
        FactorCalculator().calculate(market_frame(), "returns(close, 0)")


def test_rejects_constant_factor() -> None:
    expression = "sub(returns(close, 5), returns(close, 5))"

    with pytest.raises(FactorCalculationError, match="constant"):
        FactorCalculator().calculate(market_frame(), expression)
