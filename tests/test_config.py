import pytest
from pydantic import SecretStr

from alphabeater.config import Settings


def test_rejects_live_alpaca_configuration() -> None:
    settings = Settings(
        alpaca_api_key=SecretStr("key"),
        alpaca_secret_key=SecretStr("secret"),
        alpaca_paper=False,
    )

    with pytest.raises(ValueError, match="paper trading only"):
        settings.require_alpaca_credentials()


def test_requires_both_alpaca_keys() -> None:
    settings = Settings(alpaca_api_key=SecretStr("key"), alpaca_secret_key=None)

    with pytest.raises(ValueError, match="ALPACA_API_KEY"):
        settings.require_alpaca_credentials()
