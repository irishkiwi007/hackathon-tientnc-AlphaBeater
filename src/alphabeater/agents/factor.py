"""Constrained factor proposal agent."""

from collections.abc import Callable

from alphabeater.dsl import (
    ALLOWED_FIELDS,
    ALLOWED_OPERATORS,
    referenced_fields,
    validate_expression,
)
from alphabeater.llm.base import StructuredLLM
from alphabeater.models import FactorProposal, MarketHypothesis


class FactorAgent:
    def __init__(self, llm: StructuredLLM, *, max_attempts: int = 4) -> None:
        self._llm = llm
        self._max_attempts = max_attempts

    def propose(
        self,
        hypothesis: MarketHypothesis,
        *,
        execution_check: Callable[[str], None] | None = None,
    ) -> FactorProposal:
        feedback = ""
        last_error: ValueError | None = None
        for _ in range(self._max_attempts):
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
                    "Every expression must be a function call. Do not use +, -, *, /, "
                    "comparisons, brackets, or Python code. Use add(a,b), sub(a,b), "
                    "mul(a,b), div(a,b), and neg(a) for arithmetic. Rolling operators "
                    "take a series and a positive integer window. Valid examples: "
                    "returns(close,5) and "
                    "mul(returns(close,5),relative_volume(volume,20)). "
                    "Do not subtract or divide an expression by itself. required_fields "
                    "must list exactly the fields used in the expression. "
                    "Propose exactly five meaningfully different candidates. Avoid minor "
                    "window-only variants of the same formula."
                    f"{feedback}"
                ),
            )
            try:
                self._validate(proposal, execution_check)
            except ValueError as exc:
                last_error = exc
                rejected = [candidate.expression for candidate in proposal.candidates]
                feedback = (
                    f"\nThe previous expressions {rejected} were rejected with this error: "
                    f"{exc}. Return corrected expressions."
                )
                continue
            return proposal
        raise ValueError(f"factor generation failed after retries: {last_error}")

    @staticmethod
    def _validate(
        proposal: FactorProposal,
        execution_check: Callable[[str], None] | None,
    ) -> None:
        if len(proposal.candidates) != 5:
            raise ValueError("exactly five distinct candidates are required")
        for candidate in proposal.candidates:
            validate_expression(candidate.expression)
            unknown_fields = set(candidate.required_fields) - ALLOWED_FIELDS
            if unknown_fields:
                raise ValueError(f"candidate declares unknown fields: {sorted(unknown_fields)}")
            actual_fields = referenced_fields(candidate.expression)
            declared_fields = set(candidate.required_fields)
            if actual_fields != declared_fields:
                raise ValueError(
                    "candidate required_fields must exactly match expression fields; "
                    f"expression uses {sorted(actual_fields)}"
                )
            if execution_check is not None:
                execution_check(candidate.expression)
