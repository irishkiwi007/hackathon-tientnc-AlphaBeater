"""Environment-backed application configuration."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Secrets stay outside source control and are only required by live adapters."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: SecretStr | None = None
    gemma_model: str = "gemma-4-31b-it"

    alpaca_api_key: SecretStr | None = None
    alpaca_secret_key: SecretStr | None = None
    alpaca_paper: bool = Field(default=True)
    enable_paper_orders: bool = Field(default=False)
    enable_automatic_exits: bool = Field(default=False)

    def require_gemini_key(self) -> str:
        if self.gemini_api_key is None:
            raise ValueError("GEMINI_API_KEY is required to call Gemma")
        return self.gemini_api_key.get_secret_value()

    def assert_paper_trading(self) -> None:
        if not self.alpaca_paper:
            raise ValueError("AlphaBeater currently permits Alpaca paper trading only")

    def require_alpaca_credentials(self) -> tuple[str, str]:
        self.assert_paper_trading()
        if self.alpaca_api_key is None or self.alpaca_secret_key is None:
            raise ValueError("ALPACA_API_KEY and ALPACA_SECRET_KEY are required")
        return (
            self.alpaca_api_key.get_secret_value(),
            self.alpaca_secret_key.get_secret_value(),
        )
