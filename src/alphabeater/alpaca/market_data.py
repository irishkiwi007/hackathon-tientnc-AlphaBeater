"""Read-only stock and options market data from Alpaca."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol

from alpaca.data.enums import DataFeed, OptionsFeed
from alpaca.data.requests import OptionChainRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from pydantic import BaseModel, ConfigDict

from alphabeater.config import Settings


class StockDataClient(Protocol):
    def get_stock_bars(self, request: StockBarsRequest) -> Any: ...


class OptionDataClient(Protocol):
    def get_option_chain(self, request: OptionChainRequest) -> Any: ...


class MarketDataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StockBar(MarketDataModel):
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    vwap: Decimal | None


class OptionQuote(MarketDataModel):
    symbol: str
    quote_timestamp: datetime | None
    bid_price: Decimal | None
    bid_size: Decimal | None
    ask_price: Decimal | None
    ask_size: Decimal | None
    implied_volatility: Decimal | None
    delta: Decimal | None
    gamma: Decimal | None
    theta: Decimal | None
    vega: Decimal | None

    @property
    def spread(self) -> Decimal | None:
        if self.bid_price is None or self.ask_price is None:
            return None
        return self.ask_price - self.bid_price


def _decimal(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


class AlpacaMarketData:
    def __init__(self, stock_client: StockDataClient, option_client: OptionDataClient) -> None:
        self._stock_client = stock_client
        self._option_client = option_client

    @classmethod
    def from_settings(cls, settings: Settings) -> "AlpacaMarketData":
        from alpaca.data.historical.option import OptionHistoricalDataClient
        from alpaca.data.historical.stock import StockHistoricalDataClient

        api_key, secret_key = settings.require_alpaca_credentials()
        return cls(
            StockHistoricalDataClient(api_key, secret_key),
            OptionHistoricalDataClient(api_key, secret_key),
        )

    def get_daily_bars(
        self,
        symbols: list[str],
        *,
        start: datetime,
        end: datetime,
    ) -> list[StockBar]:
        if not symbols:
            raise ValueError("at least one stock symbol is required")
        if start >= end:
            raise ValueError("start must be earlier than end")

        request = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            feed=DataFeed.IEX,
        )
        response = self._stock_client.get_stock_bars(request)
        result: list[StockBar] = []
        for symbol, bars in response.data.items():
            result.extend(
                StockBar(
                    symbol=symbol,
                    timestamp=bar.timestamp,
                    open=Decimal(str(bar.open)),
                    high=Decimal(str(bar.high)),
                    low=Decimal(str(bar.low)),
                    close=Decimal(str(bar.close)),
                    volume=Decimal(str(bar.volume)),
                    vwap=_decimal(bar.vwap),
                )
                for bar in bars
            )
        return sorted(result, key=lambda bar: (bar.timestamp, bar.symbol))

    def get_option_chain(
        self,
        underlying_symbol: str,
        *,
        expiration_start: date,
        expiration_end: date,
        strike_min: Decimal,
        strike_max: Decimal,
    ) -> list[OptionQuote]:
        if expiration_start > expiration_end:
            raise ValueError("expiration_start must be on or before expiration_end")
        if strike_min <= 0 or strike_min >= strike_max:
            raise ValueError("strike range is invalid")

        request = OptionChainRequest(
            underlying_symbol=underlying_symbol.upper(),
            feed=OptionsFeed.INDICATIVE,
            expiration_date_gte=expiration_start,
            expiration_date_lte=expiration_end,
            strike_price_gte=float(strike_min),
            strike_price_lte=float(strike_max),
        )
        snapshots = self._option_client.get_option_chain(request)
        result: list[OptionQuote] = []
        for symbol, snapshot in snapshots.items():
            quote = snapshot.latest_quote
            greeks = snapshot.greeks
            result.append(
                OptionQuote(
                    symbol=symbol,
                    quote_timestamp=None if quote is None else quote.timestamp,
                    bid_price=None if quote is None else _decimal(quote.bid_price),
                    bid_size=None if quote is None else _decimal(quote.bid_size),
                    ask_price=None if quote is None else _decimal(quote.ask_price),
                    ask_size=None if quote is None else _decimal(quote.ask_size),
                    implied_volatility=_decimal(snapshot.implied_volatility),
                    delta=None if greeks is None else _decimal(greeks.delta),
                    gamma=None if greeks is None else _decimal(greeks.gamma),
                    theta=None if greeks is None else _decimal(greeks.theta),
                    vega=None if greeks is None else _decimal(greeks.vega),
                )
            )
        return sorted(result, key=lambda option: option.symbol)
