"""Constrained factor proposal agent."""

from alphabeater.dsl import ALLOWED_FIELDS, ALLOWED_OPERATORS, validate_expression
from alphabeater.llm.base import StructuredLLM
from alphabeater.models import FactorProposal, MarketHypothesis


class FactorAgent:
    def __init__(self, llm: StructuredLLM) -> None:
        self._llm = llm

    def propose(self, hypothesis: MarketHypothesis) -> FactorProposal:
        proposal = self._llm.generate(
            response_type=FactorProposal,
            system_prompt=(
                "You design interpretable factor candidates for deterministic testing. "
                "Do not report performance or claim that a candidate works. Use only the "
                "registered functional DSL."
            ),
            user_prompt=(
                f"Hypothesis: {hypothesis.model_dump_json()}\n"
                f"Fields: {sorted(ALLOWED_FIELDS)}\n"
                f"Operators: {sorted(ALLOWED_OPERATORS)}\n"
                "Propose one to three meaningfully different candidates."
            ),
        )
        for candidate in proposal.candidates:
            validate_expression(candidate.expression)
            unknown_fields = set(candidate.required_fields) - ALLOWED_FIELDS
            if unknown_fields:
                raise ValueError(f"candidate declares unknown fields: {sorted(unknown_fields)}")
        return proposal

