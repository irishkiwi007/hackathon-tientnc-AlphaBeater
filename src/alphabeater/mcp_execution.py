"""Submit approved paper option orders through Alpaca's official MCP server."""

from typing import Any

from fastmcp import Client

from alphabeater.config import Settings
from alphabeater.execution import PaperOrderReceipt
from alphabeater.mcp_check import alpaca_mcp_transport
from alphabeater.options_strategy import OptionTradePlan
from alphabeater.risk import RiskDecision


def _api_data(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("Alpaca MCP returned an unexpected result")
    data = value.get("data", value)
    if not isinstance(data, dict):
        raise TypeError("Alpaca MCP result did not contain an object")
    return data


class MCPPaperOrderExecutor:
    def __init__(self, settings: Settings, *, execution_enabled: bool = False) -> None:
        settings.assert_paper_trading()
        self._settings = settings
        self._execution_enabled = execution_enabled

    async def submit(self, plan: OptionTradePlan, decision: RiskDecision) -> PaperOrderReceipt:
        if not decision.approved:
            raise ValueError(
                "risk gate rejected the order: " + ", ".join(decision.rejected_reasons)
            )
        if not self._execution_enabled:
            raise ValueError("paper execution requires the explicit --execute flag")

        async with Client(
            alpaca_mcp_transport(self._settings, toolsets="trading"), timeout=30
        ) as client:
            result = await client.call_tool(
                "place_option_order",
                {
                    "symbol": plan.contract_symbol,
                    "qty": str(plan.quantity),
                    "side": "buy",
                    "type": "limit",
                    "time_in_force": "day",
                    "position_intent": "buy_to_open",
                    "limit_price": str(plan.limit_price),
                    "client_order_id": plan.client_order_id,
                },
            )
        order = _api_data(result.data)
        return PaperOrderReceipt(
            order_id=str(order["id"]),
            client_order_id=str(order["client_order_id"]),
            symbol=str(order["symbol"]),
            status=str(order["status"]),
            side=str(order["side"]),
            quantity=order["qty"],
            limit_price=order["limit_price"],
            submitted_at=order.get("submitted_at"),
        )
