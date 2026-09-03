"""Orchestration for the initial research loop."""

from alphabeater.agents import FactorAgent, IdeaAgent
from alphabeater.models import MarketObservation, ResearchBundle


class ResearchPipeline:
    def __init__(self, idea_agent: IdeaAgent, factor_agent: FactorAgent) -> None:
        self._idea_agent = idea_agent
        self._factor_agent = factor_agent

    def run(
        self,
        observation: MarketObservation,
        *,
        seed_insight: str | None = None,
    ) -> ResearchBundle:
        hypothesis = self._idea_agent.propose(observation, seed_insight=seed_insight)
        factors = self._factor_agent.propose(hypothesis)
        return ResearchBundle(hypothesis=hypothesis, factors=factors)
