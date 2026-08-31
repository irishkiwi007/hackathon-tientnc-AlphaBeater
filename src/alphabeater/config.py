"""Environment-backed application configuration."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Secrets stay outside source control and are only required by live adapters."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: SecretStr | None = None
    gemma_model: str = "gemma-4-26b-a4b-it"

    alpaca_api_key: SecretStr | None = None
    alpaca_secret_key: SecretStr | None = None
    alpaca_paper: bool = Field(default=True)

    def require_gemini_key(self) -> str:
        if self.gemini_api_key is None:
            raise ValueError("GEMINI_API_KEY is required to call Gemma")
        return self.gemini_api_key.get_secret_value()

    def assert_paper_trading(self) -> None:
        if not self.alpaca_paper:
            raise ValueError("AlphaBeater currently permits Alpaca paper trading only")

