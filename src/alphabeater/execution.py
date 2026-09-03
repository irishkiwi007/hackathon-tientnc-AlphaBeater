"""Paper-only Alpaca order execution."""

from decimal import Decimal
from typing import Any, Protocol

from alpaca.trading.enums import OrderSide, PositionIntent, TimeInForce
from alpaca.trading.requests import LimitOrderRequest
from pydantic import BaseModel, ConfigDict

from alphabeater.config import Settings
from alphabeater.options_strategy import OptionTradePlan
from alphabeater.risk import RiskDecision


class OrderClient(Protocol):
    def submit_order(self, *, order_data: LimitOrderRequest) -> Any: ...

    def get_order_by_client_id(self, client_id: str) -> Any: ...


class PaperOrderReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str
    client_order_id: str
    symbol: str
    status: str
    side: str
    quantity: Decimal
    limit_price: Decimal
    submitted_at: str | None


class PaperOrderExecutor:
    """Create idempotent buy-to-open limit orders on an Alpaca paper account."""

    def __init__(self, client: OrderClient, *, execution_enabled: bool = False) -> None:
        self._client = client
        self._execution_enabled = execution_enabled

    @classmethod
    def from_settings(cls, settings: Settings) -> "PaperOrderExecutor":
        from alpaca.trading.client import TradingClient

        api_key, secret_key = settings.require_alpaca_credentials()
        return cls(
            TradingClient(api_key, secret_key, paper=True),
            execution_enabled=settings.enable_paper_orders,
        )

    @staticmethod
    def order_request(plan: OptionTradePlan) -> LimitOrderRequest:
        return LimitOrderRequest(
            symbol=plan.contract_symbol,
            qty=float(plan.quantity),
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,
            limit_price=float(plan.limit_price),
            client_order_id=plan.client_order_id,
            position_intent=PositionIntent.BUY_TO_OPEN,
        )

    def submit(self, plan: OptionTradePlan, decision: RiskDecision) -> PaperOrderReceipt:
        if not decision.approved:
            raise ValueError(
                "risk gate rejected the order: " + ", ".join(decision.rejected_reasons)
            )
        if not self._execution_enabled:
            raise ValueError("paper execution is disabled; set ENABLE_PAPER_ORDERS=true to submit")

        try:
            existing = self._client.get_order_by_client_id(plan.client_order_id)
        except Exception as exc:
            if "not found" not in str(exc).lower() and "404" not in str(exc):
                raise
        else:
            return self._receipt(existing)

        order = self._client.submit_order(order_data=self.order_request(plan))
        return self._receipt(order)

    @staticmethod
    def _receipt(order: Any) -> PaperOrderReceipt:
        return PaperOrderReceipt(
            order_id=str(order.id),
            client_order_id=order.client_order_id,
            symbol=order.symbol,
            status=getattr(order.status, "value", str(order.status)),
            side=getattr(order.side, "value", str(order.side)),
            quantity=Decimal(str(order.qty)),
            limit_price=Decimal(str(order.limit_price)),
            submitted_at=(None if order.submitted_at is None else order.submitted_at.isoformat()),
        )
