"""Check local configuration and Alpaca paper account access."""

import json

from alpaca.common.exceptions import APIError
from requests import RequestException

from alphabeater.alpaca import AlpacaPaperAccount
from alphabeater.config import Settings


def main() -> int:
    settings = Settings()
    try:
        summary = AlpacaPaperAccount.from_settings(settings).get_summary()
    except (APIError, RequestException, ValueError) as exc:
        print(f"Alpaca setup check failed: {exc}")
        return 1

    result = summary.model_dump(mode="json")
    result["gemini_key_configured"] = settings.gemini_api_key is not None
    print(json.dumps(result, indent=2))

    if summary.trading_blocked:
        print("Warning: trading is blocked on this paper account.")
        return 1
    if summary.options_trading_level < 2:
        print("Warning: options trading level is below level 2.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
