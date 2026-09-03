"""Run a small read-only market data check."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from alpaca.common.exceptions import APIError

from alphabeater.alpaca import AlpacaMarketData
from alphabeater.config import Settings


def main() -> int:
    now = datetime.now(UTC)
    try:
        market_data = AlpacaMarketData.from_settings(Settings())
        bars = market_data.get_daily_bars(
            ["SPY"],
            start=now - timedelta(days=30),
            end=now,
        )
        if not bars:
            raise ValueError("Alpaca returned no SPY daily bars")

        latest = bars[-1]
        options = market_data.get_option_chain(
            "SPY",
            expiration_start=(now + timedelta(days=7)).date(),
            expiration_end=(now + timedelta(days=45)).date(),
            strike_min=latest.close * Decimal("0.9"),
            strike_max=latest.close * Decimal("1.1"),
        )
    except (APIError, ValueError) as exc:
        print(f"Market data check failed: {exc}")
        return 1

    quoted_options = [option for option in options if option.bid_price and option.ask_price]
    print(
        json.dumps(
            {
                "symbol": "SPY",
                "daily_bars": len(bars),
                "latest_bar_at": latest.timestamp.isoformat(),
                "latest_close": str(latest.close),
                "option_contracts": len(options),
                "option_contracts_with_quotes": len(quoted_options),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
