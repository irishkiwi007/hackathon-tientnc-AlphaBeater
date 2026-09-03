from types import SimpleNamespace

import pytest

from alphabeater.execution import PaperOrderExecutor
from alphabeater.risk import RiskDecision


def test_executor_refuses_a_rejected_plan() -> None:
    executor = PaperOrderExecutor(SimpleNamespace(), execution_enabled=True)
    decision = RiskDecision(
        approved=False,
        max_allowed_trade_loss=500,
        projected_options_exposure=600,
        checks=[],
        rejected_reasons=["single-trade maximum loss"],
        evaluated_at="2026-09-02T15:00:00Z",
    )

    with pytest.raises(ValueError, match="single-trade maximum loss"):
        executor.submit(SimpleNamespace(), decision)


def test_executor_requires_explicit_enable_switch() -> None:
    executor = PaperOrderExecutor(SimpleNamespace(), execution_enabled=False)
    decision = RiskDecision(
        approved=True,
        max_allowed_trade_loss=500,
        projected_options_exposure=400,
        checks=[],
        rejected_reasons=[],
        evaluated_at="2026-09-02T15:00:00Z",
    )

    with pytest.raises(ValueError, match="ENABLE_PAPER_ORDERS"):
        executor.submit(SimpleNamespace(), decision)
