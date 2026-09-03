"""Autonomous monitoring and exit rules for AlphaBeater paper positions."""

import argparse
import json
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

from alpaca.trading.enums import OrderSide, PositionIntent, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import GetOrdersRequest, MarketOrderRequest
from pydantic import BaseModel, ConfigDict

from alphabeater.config import Settings
from alphabeater.options_strategy import parse_occ_symbol


class MonitorClient(Protocol):
    def get_all_positions(self) -> list[Any]: ...

    def get_orders(self, *, filter: GetOrdersRequest) -> list[Any]: ...

    def get_clock(self) -> Any: ...

    def cancel_order_by_id(self, order_id: str) -> None: ...

    def submit_order(self, *, order_data: MarketOrderRequest) -> Any: ...


class ExitPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stop_loss_pct: Decimal = Decimal("0.25")
    take_profit_pct: Decimal = Decimal("0.40")
    exit_dte: int = 7
    stale_entry_minutes: int = 15


class MonitorEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    event_type: str
    symbol: str
    action: str
    reason: str
    automatic_action_taken: bool
    alpaca_id: str | None = None


class MonitorReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checked_at: datetime
    market_open: bool
    open_orders: int
    positions: int
    events: list[MonitorEvent]


class PaperPositionMonitor:
    def __init__(
        self,
        client: MonitorClient,
        *,
        policy: ExitPolicy | None = None,
        automatic_exits: bool = False,
        journal_path: Path = Path("artifacts/trading-journal.jsonl"),
    ) -> None:
        self._client = client
        self.policy = policy or ExitPolicy()
        self._automatic_exits = automatic_exits
        self._journal_path = journal_path

    @classmethod
    def from_settings(cls, settings: Settings) -> "PaperPositionMonitor":
        from alpaca.trading.client import TradingClient

        api_key, secret_key = settings.require_alpaca_credentials()
        return cls(
            TradingClient(api_key, secret_key, paper=True),
            automatic_exits=settings.enable_automatic_exits,
        )

    def check_once(self, *, now: datetime | None = None) -> MonitorReport:
        checked_at = now or datetime.now(UTC)
        clock = self._client.get_clock()
        market_open = bool(clock.is_open)
        orders = self._client.get_orders(filter=GetOrdersRequest(status=QueryOrderStatus.OPEN))
        positions = self._client.get_all_positions()
        events: list[MonitorEvent] = []

        for order in orders:
            event = self._inspect_order(order, checked_at, market_open)
            if event is not None:
                events.append(event)
        for position in positions:
            event = self._inspect_position(position, checked_at, market_open)
            if event is not None:
                events.append(event)

        report = MonitorReport(
            checked_at=checked_at,
            market_open=market_open,
            open_orders=len(orders),
            positions=len(positions),
            events=events,
        )
        self._append_journal(report)
        return report

    def _inspect_order(
        self, order: Any, checked_at: datetime, market_open: bool
    ) -> MonitorEvent | None:
        submitted_at = order.submitted_at
        if submitted_at is None:
            return None
        age_minutes = (checked_at - submitted_at).total_seconds() / 60
        if age_minutes < self.policy.stale_entry_minutes:
            return None
        can_act = self._automatic_exits and market_open
        if can_act:
            self._client.cancel_order_by_id(str(order.id))
        return MonitorEvent(
            timestamp=checked_at,
            event_type="stale_entry_order",
            symbol=order.symbol,
            action="cancel" if can_act else "recommend_cancel",
            reason=f"entry order has been open for {age_minutes:.0f} minutes",
            automatic_action_taken=can_act,
            alpaca_id=str(order.id),
        )

    def _inspect_position(
        self, position: Any, checked_at: datetime, market_open: bool
    ) -> MonitorEvent | None:
        asset_class = getattr(position.asset_class, "value", str(position.asset_class))
        if asset_class != "us_option":
            return None
        cost_basis = abs(Decimal(str(position.cost_basis)))
        market_value = abs(Decimal(str(position.market_value)))
        return_pct = Decimal(0) if cost_basis == 0 else (market_value - cost_basis) / cost_basis
        contract = parse_occ_symbol(position.symbol)
        dte = (contract.expiration - checked_at.date()).days

        reason: str | None = None
        if return_pct <= -self.policy.stop_loss_pct:
            reason = f"position return {return_pct:.1%} reached stop-loss threshold"
        elif return_pct >= self.policy.take_profit_pct:
            reason = f"position return {return_pct:.1%} reached take-profit threshold"
        elif dte <= self.policy.exit_dte:
            reason = f"contract has {dte} days to expiry"
        if reason is None:
            return None

        can_act = self._automatic_exits and market_open
        order_id = None
        if can_act:
            order = self._client.submit_order(
                order_data=MarketOrderRequest(
                    symbol=position.symbol,
                    qty=abs(float(position.qty)),
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY,
                    position_intent=PositionIntent.SELL_TO_CLOSE,
                    client_order_id=(
                        f"alphabeater-exit-{checked_at:%Y%m%d%H%M%S}-{position.symbol}"[:48]
                    ),
                )
            )
            order_id = str(order.id)
        return MonitorEvent(
            timestamp=checked_at,
            event_type="position_exit_rule",
            symbol=position.symbol,
            action="sell_to_close" if can_act else "recommend_sell_to_close",
            reason=reason,
            automatic_action_taken=can_act,
            alpaca_id=order_id,
        )

    def _append_journal(self, report: MonitorReport) -> None:
        self._journal_path.parent.mkdir(parents=True, exist_ok=True)
        with self._journal_path.open("a", encoding="utf-8") as handle:
            handle.write(report.model_dump_json() + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor AlphaBeater paper orders and positions")
    parser.add_argument("--watch", action="store_true", help="continue checking until stopped")
    parser.add_argument("--interval", type=int, default=30, help="seconds between checks")
    args = parser.parse_args()
    if args.interval < 10:
        parser.error("--interval must be at least 10 seconds")

    monitor = PaperPositionMonitor.from_settings(Settings())
    try:
        while True:
            report = monitor.check_once()
            print(json.dumps(report.model_dump(mode="json"), indent=2))
            if not args.watch:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
