"""The sign of a factor is chosen by measurement, not by the model's guess.

Selection uses training and validation only. The locked test must not influence which direction
is picked, or the holdout stops being an honest out-of-sample check.
"""

from datetime import UTC, datetime, timedelta

import pandas as pd

from alphabeater.agent_run import _resolve_direction
from alphabeater.backtest import FactorBacktester
from alphabeater.models import Direction, FactorCandidate


def trending_frame() -> pd.DataFrame:
    """One symbol drifting up, one drifting down, so direction genuinely matters."""
    rows = []
    start = datetime(2024, 1, 1, tzinfo=UTC)
    for symbol, drift in [("SPY", 0.6), ("QQQ", -0.4), ("IWM", 0.2)]:
        price = 100.0
        for day in range(400):
            price = max(5.0, price + drift + ((day % 7) - 3) * 0.35)
            rows.append(
                {
                    "symbol": symbol,
                    "timestamp": start + timedelta(days=day),
                    "open": price - 0.5,
                    "high": price + 0.8,
                    "low": price - 0.9,
                    "close": price,
                    "volume": 1_000_000 + (day % 11) * 5_000,
                    "vwap": price - 0.1,
                }
            )
    return pd.DataFrame(rows)


def candidate(direction: Direction) -> FactorCandidate:
    return FactorCandidate(
        name="momentum_20",
        expression="returns(close,20)",
        rationale="Twenty session momentum should persist over the coming month.",
        required_fields=["close"],
        horizon_days=20,
        expected_direction=direction,
    )


def test_returns_a_candidate_and_a_development_result() -> None:
    resolved, result = _resolve_direction(
        FactorBacktester(), trending_frame(), candidate(Direction.POSITIVE)
    )

    assert resolved.expression == "returns(close,20)"
    assert result.training.observations > 0
    assert result.validation.observations > 0


def test_the_same_direction_is_chosen_regardless_of_the_models_guess() -> None:
    """The measurement decides, so both starting guesses must converge on one answer."""
    frame = trending_frame()
    backtester = FactorBacktester()

    from_positive, _ = _resolve_direction(backtester, frame, candidate(Direction.POSITIVE))
    from_negative, _ = _resolve_direction(backtester, frame, candidate(Direction.NEGATIVE))

    assert from_positive.expected_direction == from_negative.expected_direction


def test_the_returned_result_matches_the_returned_direction() -> None:
    """Later stages re-run the holdout using the resolved direction, so they must agree."""
    frame = trending_frame()
    backtester = FactorBacktester()
    resolved, result = _resolve_direction(backtester, frame, candidate(Direction.POSITIVE))

    expected = backtester.run_development(frame, resolved.expression, resolved.expected_direction)

    assert result.training.sharpe_ratio == expected.training.sharpe_ratio
    assert result.validation.sharpe_ratio == expected.validation.sharpe_ratio


def test_the_chosen_direction_is_no_worse_than_the_alternative() -> None:
    frame = trending_frame()
    backtester = FactorBacktester()
    resolved, result = _resolve_direction(backtester, frame, candidate(Direction.POSITIVE))

    other = (
        Direction.NEGATIVE
        if resolved.expected_direction == Direction.POSITIVE
        else Direction.POSITIVE
    )
    alternative = backtester.run_development(frame, resolved.expression, other)

    chosen_worst = min(result.training.sharpe_ratio, result.validation.sharpe_ratio)
    other_worst = min(alternative.training.sharpe_ratio, alternative.validation.sharpe_ratio)
    assert chosen_worst >= other_worst


def test_all_other_fields_are_preserved_when_the_direction_flips() -> None:
    original = candidate(Direction.POSITIVE)
    resolved, _ = _resolve_direction(FactorBacktester(), trending_frame(), original)

    assert resolved.name == original.name
    assert resolved.rationale == original.rationale
    assert resolved.horizon_days == original.horizon_days
    assert resolved.required_fields == original.required_fields
