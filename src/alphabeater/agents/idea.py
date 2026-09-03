"""Evidence-grounded hypothesis generation."""

from alphabeater.llm.base import StructuredLLM
from alphabeater.models import MarketHypothesis, MarketObservation


class IdeaAgent:
    def __init__(self, llm: StructuredLLM) -> None:
        self._llm = llm

    def propose(
        self,
        observation: MarketObservation,
        *,
        seed_insight: str | None = None,
    ) -> MarketHypothesis:
        seed = seed_insight or "No human seed insight was supplied."
        return self._llm.generate(
            response_type=MarketHypothesis,
            system_prompt=(
                "You are a skeptical quantitative researcher. Use only the supplied "
                "point-in-time evidence. Produce one testable mechanism, not a trade. "
                "Include conditions that would falsify it and never invent statistics."
            ),
            user_prompt=(
                f"Snapshot: {observation.model_dump_json()}\nOptional researcher insight: {seed}"
            ),
        )
