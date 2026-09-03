"""Turn a validated factor into a defined-risk options trade plan."""

import hashlib
import re
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from alphabeater.alpaca.market_data import OptionQuote
from alphabeater.factor_calculator import FactorCalculator
from alphabeater.models import Direction, FactorCandidate

OCC_SYMBOL = re.compile(r"^(?P<root>[A-Z]{1,6})(?P<date>\d{6})(?P<right>[CP])(?P<strike>\d{8})$")


class OptionRight(StrEnum):
    CALL = "call"
    PUT = "put"


class OptionContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    underlying: str
    expiration: date
    right: OptionRight
    strike: Decimal


class FactorSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    underlying: str
    raw_value: float
    z_score: float
    predicted_score: float
    right: OptionRight
    as_of: datetime


class OptionTradePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_order_id: str = Field(max_length=48)
    underlying: str
    contract_symbol: str
    right: OptionRight
    expiration: date
    strike: Decimal
    quantity: int = Field(ge=1)
    limit_price: Decimal = Field(gt=0)
    maximum_loss: Decimal = Field(gt=0)
    bid_price: Decimal = Field(gt=0)
    ask_price: Decimal = Field(gt=0)
    relative_spread: Decimal = Field(ge=0)
    delta: Decimal
    quote_timestamp: datetime
    factor_name: str
    factor_expression: str
    signal: FactorSignal
    rationale: str
    created_at: datetime


def parse_occ_symbol(symbol: str) -> OptionContract:
    match = OCC_SYMBOL.fullmatch(symbol.upper())
    if match is None:
        raise ValueError(f"invalid OCC option symbol: {symbol}")
    compact_date = match.group("date")
    expiration = date(
        2000 + int(compact_date[:2]),
        int(compact_date[2:4]),
        int(compact_date[4:]),
    )
    return OptionContract(
        symbol=symbol.upper(),
        underlying=match.group("root"),
        expiration=expiration,
        right=OptionRight.CALL if match.group("right") == "C" else OptionRight.PUT,
        strike=Decimal(match.group("strike")) / Decimal(1000),
    )


class LongPremiumStrategy:
    """Buy one liquid call or put. Premium paid is the maximum possible loss."""

    def __init__(
        self,
        *,
        min_dte: int = 21,
        max_dte: int = 45,
        min_abs_delta: Decimal = Decimal("0.35"),
        max_abs_delta: Decimal = Decimal("0.60"),
        max_relative_spread: Decimal = Decimal("0.20"),
        signal_lookback: int = 60,
    ) -> None:
        if not 1 <= min_dte <= max_dte:
            raise ValueError("DTE range is invalid")
        self._min_dte = min_dte
        self._max_dte = max_dte
        self._min_abs_delta = min_abs_delta
        self._max_abs_delta = max_abs_delta
        self._max_relative_spread = max_relative_spread
        self._signal_lookback = signal_lookback

    def derive_signal(
        self,
        frame: pd.DataFrame,
        candidate: FactorCandidate,
    ) -> FactorSignal:
        return self.derive_signals(frame, candidate)[0]

    def derive_signals(
        self,
        frame: pd.DataFrame,
        candidate: FactorCandidate,
    ) -> list[FactorSignal]:
        ordered = frame.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
        values = FactorCalculator().calculate(ordered, candidate.expression)
        signals = ordered[["symbol", "timestamp"]].copy()
        signals["value"] = values
        latest: list[FactorSignal] = []
        multiplier = 1.0 if candidate.expected_direction == Direction.POSITIVE else -1.0

        for symbol, group in signals.groupby("symbol"):
            valid = group.dropna(subset=["value"]).tail(self._signal_lookback)
            if len(valid) < 10:
                continue
            current = float(valid.iloc[-1]["value"])
            standard_deviation = float(valid["value"].std(ddof=1))
            if standard_deviation == 0:
                continue
            z_score = (current - float(valid["value"].mean())) / standard_deviation
            predicted_score = z_score * multiplier
            latest.append(
                FactorSignal(
                    underlying=str(symbol),
                    raw_value=current,
                    z_score=z_score,
                    predicted_score=predicted_score,
                    right=OptionRight.CALL if predicted_score >= 0 else OptionRight.PUT,
                    as_of=pd.Timestamp(valid.iloc[-1]["timestamp"]).to_pydatetime(),
                )
            )

        if not latest:
            raise ValueError("factor did not produce a usable current signal")
        return sorted(latest, key=lambda signal: abs(signal.predicted_score), reverse=True)

    def build_plan(
        self,
        signal: FactorSignal,
        candidate: FactorCandidate,
        quotes: list[OptionQuote],
        *,
        quantity: int = 1,
        maximum_loss_budget: Decimal | None = None,
        now: datetime | None = None,
    ) -> OptionTradePlan:
        if quantity < 1:
            raise ValueError("quantity must be positive")
        created_at = now or datetime.now(UTC)
        if maximum_loss_budget is not None and maximum_loss_budget <= 0:
            raise ValueError("maximum loss budget must be positive")
        ranked: list[
            tuple[Decimal, Decimal, int, OptionContract, OptionQuote, Decimal]
        ] = []

        for quote in quotes:
            try:
                contract = parse_occ_symbol(quote.symbol)
            except ValueError:
                continue
            days = (contract.expiration - created_at.date()).days
            if contract.underlying != signal.underlying or contract.right != signal.right:
                continue
            if not self._min_dte <= days <= self._max_dte:
                continue
            if (
                quote.quote_timestamp is None
                or quote.bid_price is None
                or quote.ask_price is None
                or quote.delta is None
                or quote.bid_price <= 0
                or quote.ask_price <= quote.bid_price
            ):
                continue
            absolute_delta = abs(quote.delta)
            midpoint = (quote.bid_price + quote.ask_price) / 2
            relative_spread = (quote.ask_price - quote.bid_price) / midpoint
            if not self._min_abs_delta <= absolute_delta <= self._max_abs_delta:
                continue
            if relative_spread > self._max_relative_spread:
                continue
            limit_price = midpoint.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            maximum_loss = limit_price * Decimal(100 * quantity)
            if maximum_loss_budget is not None and maximum_loss > maximum_loss_budget:
                continue
            ranked.append(
                (
                    abs(absolute_delta - Decimal("0.50")),
                    relative_spread,
                    abs(days - 30),
                    contract,
                    quote,
                    limit_price,
                )
            )

        if not ranked:
            budget_text = (
                " and premium budget" if maximum_loss_budget is not None else ""
            )
            raise ValueError(
                "no option contract passed the DTE, delta, quote, spread"
                f"{budget_text} filters"
            )
        _, relative_spread, _, contract, quote, limit_price = min(
            ranked, key=lambda item: item[:3]
        )
        assert quote.bid_price is not None
        assert quote.ask_price is not None
        assert quote.delta is not None
        assert quote.quote_timestamp is not None
        maximum_loss = limit_price * Decimal(100 * quantity)
        identifier = hashlib.sha256(
            f"{contract.symbol}:{candidate.name}:{signal.as_of.isoformat()}".encode()
        ).hexdigest()[:20]
        return OptionTradePlan(
            client_order_id=f"alphabeater-{identifier}",
            underlying=contract.underlying,
            contract_symbol=contract.symbol,
            right=contract.right,
            expiration=contract.expiration,
            strike=contract.strike,
            quantity=quantity,
            limit_price=limit_price,
            maximum_loss=maximum_loss,
            bid_price=quote.bid_price,
            ask_price=quote.ask_price,
            relative_spread=relative_spread,
            delta=quote.delta,
            quote_timestamp=quote.quote_timestamp,
            factor_name=candidate.name,
            factor_expression=candidate.expression,
            signal=signal,
            rationale=(
                f"Long {contract.right.value} from a {signal.predicted_score:.2f} directional "
                f"factor z-score; {contract.expiration.isoformat()} expiry, "
                f"{abs(quote.delta):.2f} absolute delta, {relative_spread:.1%} spread."
            ),
            created_at=created_at,
        )
