"""Read-only access to an Alpaca paper account."""

from decimal import Decimal
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

from alphabeater.config import Settings


class AccountClient(Protocol):
    def get_account(self) -> Any: ...


class PaperAccountSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str
    account_number: str
    status: str
    currency: str
    equity: Decimal
    buying_power: Decimal
    options_buying_power: Decimal
    options_approved_level: int
    options_trading_level: int
    trading_blocked: bool


class AlpacaPaperAccount:
    """Expose account status without providing any order methods."""

    def __init__(self, client: AccountClient) -> None:
        self._client = client

    @classmethod
    def from_settings(cls, settings: Settings) -> "AlpacaPaperAccount":
        from alpaca.trading.client import TradingClient

        api_key, secret_key = settings.require_alpaca_credentials()
        client = TradingClient(api_key, secret_key, paper=True)
        return cls(client)

    def get_summary(self) -> PaperAccountSummary:
        account = self._client.get_account()
        return PaperAccountSummary(
            account_id=str(account.id),
            account_number=account.account_number,
            status=str(account.status),
            currency=account.currency or "USD",
            equity=Decimal(account.equity or "0"),
            buying_power=Decimal(account.buying_power or "0"),
            options_buying_power=Decimal(account.options_buying_power or "0"),
            options_approved_level=account.options_approved_level or 0,
            options_trading_level=account.options_trading_level or 0,
            trading_blocked=bool(account.trading_blocked),
        )

