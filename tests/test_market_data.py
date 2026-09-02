from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from alphabeater.alpaca import AlpacaMarketData


class FakeStockClient:
    def get_stock_bars(self, request: object) -> SimpleNamespace:
        bar = SimpleNamespace(
            timestamp=datetime(2026, 9, 1, tzinfo=UTC),
            open=640.0,
            high=645.0,
            low=639.0,
            close=644.0,
            volume=50_000_000,
            vwap=642.5,
        )
        return SimpleNamespace(data={"SPY": [bar]})


class FakeOptionClient:
    def get_option_chain(self, request: object) -> dict[str, SimpleNamespace]:
        quote = SimpleNamespace(
            timestamp=datetime(2026, 9, 1, 20, 0, tzinfo=UTC),
            bid_price=5.10,
            bid_size=20,
            ask_price=5.30,
            ask_size=18,
        )
        greeks = SimpleNamespace(delta=0.51, gamma=0.02, theta=-0.08, vega=0.15)
        snapshot = SimpleNamespace(latest_quote=quote, greeks=greeks, implied_volatility=0.22)
        return {"SPY261002C00645000": snapshot}


def test_reads_daily_bars() -> None:
    data = AlpacaMarketData(FakeStockClient(), FakeOptionClient())

    bars = data.get_daily_bars(
        ["SPY"],
        start=datetime(2026, 8, 1, tzinfo=UTC),
        end=datetime(2026, 9, 2, tzinfo=UTC),
    )

    assert bars[0].symbol == "SPY"
    assert bars[0].close == Decimal("644.0")


def test_reads_option_chain_and_computes_spread() -> None:
    data = AlpacaMarketData(FakeStockClient(), FakeOptionClient())

    options = data.get_option_chain(
        "SPY",
        expiration_start=date(2026, 9, 7),
        expiration_end=date(2026, 10, 16),
        strike_min=Decimal(580),
        strike_max=Decimal(710),
    )

    assert options[0].delta == Decimal("0.51")
    assert options[0].spread == Decimal("0.20")


def test_rejects_invalid_date_range() -> None:
    data = AlpacaMarketData(FakeStockClient(), FakeOptionClient())

    with pytest.raises(ValueError, match="expiration_start"):
        data.get_option_chain(
            "SPY",
            expiration_start=date(2026, 10, 1),
            expiration_end=date(2026, 9, 1),
            strike_min=Decimal(500),
            strike_max=Decimal(700),
        )
