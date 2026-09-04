"""The prompt's declared arities must match what the calculator actually enforces.

A mismatch here is invisible in unit tests but fatal in production: the model is told the
wrong signature, writes an expression the calculator rejects, and factor generation fails
after burning its retries. That is exactly what `zscore(series, window)` did.
"""

import re
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from alphabeater.dsl import ALLOWED_OPERATORS, OPERATOR_SIGNATURES
from alphabeater.factor_calculator import FactorCalculator

WINDOWLESS = {"rank", "zscore", "demean"}


def market_frame() -> pd.DataFrame:
    rows = []
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for symbol, offset in [("SPY", 0), ("QQQ", 20)]:
        for day in range(40):
            price = 100 + offset + day + (day % 5)
            rows.append(
                {
                    "symbol": symbol,
                    "timestamp": start + timedelta(days=day),
                    "open": price - 1,
                    "high": price + 1,
                    "low": price - 2,
                    "close": price,
                    "volume": 1_000 + 10 * day + offset,
                    "vwap": price - 0.25,
                }
            )
    return pd.DataFrame(rows)


def declared_arity(name: str) -> int:
    """Count the arguments in the published signature, ignoring the trailing comment."""
    signature = OPERATOR_SIGNATURES[name].split("#")[0].strip()
    inside = re.search(r"\((.*)\)", signature)
    assert inside, f"malformed signature for {name}"
    return len([part for part in inside.group(1).split(",") if part.strip()])


def test_every_operator_has_a_published_signature() -> None:
    assert set(OPERATOR_SIGNATURES) == set(ALLOWED_OPERATORS)


def test_rank_and_zscore_are_documented_as_single_argument() -> None:
    for name in WINDOWLESS:
        assert declared_arity(name) == 1
        assert "NO window" in OPERATOR_SIGNATURES[name]


@pytest.mark.parametrize("name", sorted(ALLOWED_OPERATORS))
def test_declared_arity_is_accepted_by_the_calculator(name: str) -> None:
    """Build a real expression at the declared arity and run it through the real calculator."""
    frame = market_frame()
    arity = declared_arity(name)

    if name == "relative_volume":
        expression = "relative_volume(volume, 5)"
    elif name == "ts_corr":
        expression = "ts_corr(close, volume, 5)"
    elif name == "sign":
        # sign(close) is constantly 1 on positive prices, which the calculator rejects by
        # design; sign is meaningful on a series that changes direction.
        expression = "sign(returns(close, 5))"
    elif name in WINDOWLESS or arity == 1:
        expression = f"{name}(close)"
    elif name in {"add", "sub", "mul", "div"}:
        expression = f"{name}(close, volume)"
    else:
        expression = f"{name}(close, 5)"

    result = FactorCalculator().calculate(frame, expression)
    assert len(result) == len(frame)


@pytest.mark.parametrize("name", sorted(WINDOWLESS))
def test_giving_a_window_to_a_cross_sectional_operator_is_rejected(name: str) -> None:
    """This is the exact mistake the old prompt invited."""
    with pytest.raises(ValueError, match="expects 1 arguments"):
        FactorCalculator().calculate(market_frame(), f"{name}(close, 20)")
