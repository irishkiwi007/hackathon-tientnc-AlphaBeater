"""Run the research agents on recent Alpaca data."""

import json
from datetime import UTC, datetime, timedelta

import pandas as pd
from alpaca.common.exceptions import APIError

from alphabeater.agents import FactorAgent, IdeaAgent
from alphabeater.alpaca import AlpacaMarketData, StockBar
from alphabeater.backtest import FactorBacktester
from alphabeater.config import Settings
from alphabeater.factor_calculator import FactorCalculator
from alphabeater.llm import GemmaLLM
from alphabeater.models import MarketObservation


def _to_frame(bars: list[StockBar]) -> pd.DataFrame:
    frame = pd.DataFrame([bar.model_dump() for bar in bars])
    numeric_columns = ["open", "high", "low", "close", "volume", "vwap"]
    frame[numeric_columns] = frame[numeric_columns].apply(pd.to_numeric)
    return frame


def _evidence(frame: pd.DataFrame) -> list[str]:
    evidence = []
    for symbol, values in frame.groupby("symbol"):
        ordered = values.sort_values("timestamp")
        latest = ordered.iloc[-1]
        return_5d = latest["close"] / ordered.iloc[-6]["close"] - 1
        volume_ratio = latest["volume"] / ordered.tail(20)["volume"].mean()
        evidence.append(
            f"{symbol}: 5-day return {return_5d:.2%}; "
            f"latest volume is {volume_ratio:.2f} times its 20-day mean"
        )
    return evidence


def main() -> int:
    settings = Settings()
    now = datetime.now(UTC)
    try:
        market_data = AlpacaMarketData.from_settings(settings)
        bars = market_data.get_daily_bars(
            ["SPY", "QQQ", "IWM"],
            start=now - timedelta(days=420),
            end=now,
        )
        frame = _to_frame(bars)
        observation = MarketObservation(
            as_of=max(bar.timestamp for bar in bars).isoformat(),
            universe=["SPY", "QQQ", "IWM"],
            evidence=_evidence(frame),
        )
        llm = GemmaLLM(
            api_key=settings.require_gemini_key(),
            model=settings.gemma_model,
        )
        hypothesis = IdeaAgent(llm).propose(observation)
        calculator = FactorCalculator()

        def execution_check(expression: str) -> None:
            calculator.calculate(frame, expression)

        factors = FactorAgent(llm).propose(hypothesis, execution_check=execution_check)
        backtester = FactorBacktester()
        output = {
            "hypothesis": hypothesis.model_dump(mode="json"),
            "factors": [],
        }
        for candidate in factors.candidates:
            values = calculator.calculate(frame, candidate.expression)
            backtest = backtester.run(
                frame,
                candidate.expression,
                candidate.expected_direction,
            )
            output["factors"].append(
                {
                    **candidate.model_dump(mode="json"),
                    "calculated_values": int(values.notna().sum()),
                    "backtest": backtest.model_dump(mode="json"),
                }
            )
    except (APIError, ValueError) as exc:
        print(f"Research demo failed: {exc}")
        return 1

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
