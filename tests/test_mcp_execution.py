import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Self

from pydantic import SecretStr

from alphabeater.config import Settings
from alphabeater.mcp_execution import MCPPaperOrderExecutor
from alphabeater.models import Direction, FactorCandidate
from alphabeater.options_strategy import FactorSignal, OptionRight, OptionTradePlan
from alphabeater.risk import RiskDecision


class MCPClient:
    def __init__(self) -> None:
        self.arguments = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def call_tool(self, name: str, arguments: dict[str, str]) -> SimpleNamespace:
        assert name == "place_option_order"
        self.arguments = arguments
        return SimpleNamespace(
            data={
                "_alpaca_mcp_security": {"trust": "untrusted_tool_output"},
                "data": {
                    "id": "paper-order-id",
                    "client_order_id": arguments["client_order_id"],
                    "symbol": arguments["symbol"],
                    "status": "accepted",
                    "side": "buy",
                    "qty": arguments["qty"],
                    "limit_price": arguments["limit_price"],
                    "submitted_at": "2026-09-03T14:31:00Z",
                },
            }
        )


def test_mcp_executor_routes_approved_option_order(monkeypatch: object) -> None:
    client = MCPClient()
    monkeypatch.setattr("alphabeater.mcp_execution.Client", lambda *args, **kwargs: client)
    monkeypatch.setattr(
        "alphabeater.mcp_execution.alpaca_mcp_transport", lambda *args, **kwargs: object()
    )
    now = datetime(2026, 9, 3, 14, 31, tzinfo=UTC)
    candidate = FactorCandidate(
        name="momentum_signal",
        expression="returns(close, 5)",
        rationale="Tests whether recent momentum continues into the next holding period.",
        required_fields=["close"],
        horizon_days=5,
        expected_direction=Direction.POSITIVE,
    )
    signal = FactorSignal(
        underlying="SPY",
        raw_value=0.02,
        z_score=1.2,
        predicted_score=1.2,
        right=OptionRight.CALL,
        as_of=now,
    )
    plan = OptionTradePlan(
        client_order_id="alphabeater-test-mcp",
        underlying="SPY",
        contract_symbol="SPY260925C00500000",
        right=OptionRight.CALL,
        expiration=date(2026, 9, 25),
        strike=Decimal(500),
        quantity=1,
        limit_price=Decimal("4.00"),
        maximum_loss=Decimal(400),
        bid_price=Decimal("3.90"),
        ask_price=Decimal("4.10"),
        relative_spread=Decimal("0.05"),
        delta=Decimal("0.50"),
        quote_timestamp=now,
        factor_name=candidate.name,
        factor_expression=candidate.expression,
        signal=signal,
        rationale="A liquid, defined-risk paper options position from a validated signal.",
        created_at=now,
    )
    decision = RiskDecision(
        approved=True,
        max_allowed_trade_loss=500,
        projected_options_exposure=400,
        checks=[],
        rejected_reasons=[],
        evaluated_at=now,
    )
    settings = Settings(
        alpaca_api_key=SecretStr("paper-key"),
        alpaca_secret_key=SecretStr("paper-secret"),
    )

    receipt = asyncio.run(
        MCPPaperOrderExecutor(settings, execution_enabled=True).submit(plan, decision)
    )

    assert receipt.status == "accepted"
    assert client.arguments["position_intent"] == "buy_to_open"
    assert client.arguments["type"] == "limit"
