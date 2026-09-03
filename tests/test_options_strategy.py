from datetime import UTC, datetime, timedelta
from decimal import Decimal

from alphabeater.alpaca import OptionQuote
from alphabeater.models import Direction, FactorCandidate
from alphabeater.options_strategy import (
    FactorSignal,
    LongPremiumStrategy,
    OptionRight,
    parse_occ_symbol,
)


def candidate() -> FactorCandidate:
    return FactorCandidate(
        name="momentum_signal",
        expression="returns(close, 5)",
        rationale="Tests whether recent momentum continues into the next holding period.",
        required_fields=["close"],
        horizon_days=5,
        expected_direction=Direction.POSITIVE,
    )


def quote(symbol: str, *, delta: str, bid: str, ask: str) -> OptionQuote:
    return OptionQuote(
        symbol=symbol,
        quote_timestamp=datetime(2026, 9, 2, 14, 30, tzinfo=UTC),
        bid_price=Decimal(bid),
        bid_size=Decimal(10),
        ask_price=Decimal(ask),
        ask_size=Decimal(12),
        implied_volatility=Decimal("0.20"),
        delta=Decimal(delta),
        gamma=Decimal("0.02"),
        theta=Decimal("-0.05"),
        vega=Decimal("0.10"),
    )


def test_parses_occ_symbol() -> None:
    contract = parse_occ_symbol("SPY260925C00500000")

    assert contract.underlying == "SPY"
    assert contract.expiration.isoformat() == "2026-09-25"
    assert contract.right == OptionRight.CALL
    assert contract.strike == 500


def test_selects_liquid_near_fifty_delta_contract() -> None:
    now = datetime(2026, 9, 2, 14, 31, tzinfo=UTC)
    signal = FactorSignal(
        underlying="SPY",
        raw_value=0.02,
        z_score=1.2,
        predicted_score=1.2,
        right=OptionRight.CALL,
        as_of=now - timedelta(days=1),
    )
    quotes = [
        quote("SPY260925C00500000", delta="0.49", bid="4.90", ask="5.10"),
        quote("SPY260925C00510000", delta="0.37", bid="2.50", ask="2.70"),
        quote("SPY260925P00500000", delta="-0.51", bid="4.80", ask="5.00"),
    ]

    plan = LongPremiumStrategy().build_plan(signal, candidate(), quotes, now=now)

    assert plan.contract_symbol == "SPY260925C00500000"
    assert plan.limit_price == Decimal("5.00")
    assert plan.maximum_loss == Decimal("500.00")
    assert plan.client_order_id.startswith("alphabeater-")
