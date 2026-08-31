from collections import deque
from typing import Any

from pydantic import BaseModel

from alphabeater.agents import FactorAgent, IdeaAgent
from alphabeater.models import MarketObservation
from alphabeater.pipeline import ResearchPipeline


class FakeLLM:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = deque(responses)

    def generate(
        self,
        *,
        response_type: type[BaseModel],
        system_prompt: str,
        user_prompt: str,
    ) -> BaseModel:
        return response_type.model_validate(self.responses.popleft())


def test_research_pipeline_produces_validated_bundle() -> None:
    llm = FakeLLM(
        [
            {
                "title": "Short-horizon volume-backed momentum",
                "mechanism": "Price moves accompanied by unusual volume may persist briefly as information diffuses.",
                "expected_direction": "positive",
                "horizon_days": 5,
                "evidence_used": ["SPY five-day return rose while volume exceeded its recent mean"],
                "falsification_criteria": ["Walk-forward rank IC is non-positive after costs"],
            },
            {
                "candidates": [
                    {
                        "name": "volume_backed_momentum",
                        "expression": "mul(returns(close, 5), relative_volume(volume, 20))",
                        "rationale": "Combines recent direction with a bounded proxy for participation.",
                        "required_fields": ["close", "volume"],
                        "horizon_days": 5,
                        "expected_direction": "positive",
                    }
                ]
            },
        ]
    )
    pipeline = ResearchPipeline(IdeaAgent(llm), FactorAgent(llm))
    observation = MarketObservation(
        as_of="2026-08-28T20:00:00Z",
        universe=["SPY"],
        evidence=["SPY five-day return rose while volume exceeded its recent mean"],
    )

    result = pipeline.run(observation)

    assert result.hypothesis.horizon_days == 5
    assert result.factors.candidates[0].name == "volume_backed_momentum"

