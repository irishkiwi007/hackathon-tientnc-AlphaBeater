import pytest
from pydantic import BaseModel

from alphabeater.llm.fallback import FallbackLLM


class Reply(BaseModel):
    value: str


class StubLLM:
    """Returns a fixed reply, or raises, and counts how often it was called."""

    def __init__(self, *, value: str | None = None, error: Exception | None = None) -> None:
        self._value = value
        self._error = error
        self.calls = 0

    def generate(
        self,
        *,
        response_type: type[Reply],
        system_prompt: str,
        user_prompt: str,
    ) -> Reply:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return response_type(value=self._value or "")


def _generate(llm: FallbackLLM) -> Reply:
    return llm.generate(response_type=Reply, system_prompt="sys", user_prompt="user")


def test_uses_primary_when_it_succeeds() -> None:
    primary = StubLLM(value="primary")
    secondary = StubLLM(value="secondary")

    result = _generate(FallbackLLM(primary=primary, secondary=secondary))

    assert result.value == "primary"
    assert secondary.calls == 0


def test_falls_back_to_secondary_when_primary_fails() -> None:
    primary = StubLLM(error=RuntimeError("503 UNAVAILABLE"))
    secondary = StubLLM(value="secondary")
    llm = FallbackLLM(primary=primary, secondary=secondary)

    result = _generate(llm)

    assert result.value == "secondary"
    assert primary.calls == 1
    assert secondary.calls == 1


def test_records_which_provider_answered() -> None:
    primary = StubLLM(error=RuntimeError("down"))
    secondary = StubLLM(value="secondary")
    llm = FallbackLLM(primary=primary, secondary=secondary)

    assert llm.last_provider is None
    _generate(llm)
    assert llm.last_provider == "secondary"


def test_counts_fallbacks_for_the_audit_record() -> None:
    primary = StubLLM(error=RuntimeError("down"))
    llm = FallbackLLM(primary=primary, secondary=StubLLM(value="ok"))

    _generate(llm)
    _generate(llm)

    assert llm.fallback_count == 2


def test_raises_when_both_providers_fail() -> None:
    llm = FallbackLLM(
        primary=StubLLM(error=RuntimeError("primary down")),
        secondary=StubLLM(error=RuntimeError("secondary down")),
    )

    with pytest.raises(RuntimeError, match="both LLM providers failed"):
        _generate(llm)


def test_reports_both_errors_when_both_fail() -> None:
    llm = FallbackLLM(
        primary=StubLLM(error=RuntimeError("primary boom")),
        secondary=StubLLM(error=RuntimeError("secondary boom")),
    )

    with pytest.raises(RuntimeError) as excinfo:
        _generate(llm)

    assert "primary boom" in str(excinfo.value)
    assert "secondary boom" in str(excinfo.value)


def test_without_a_secondary_the_primary_error_propagates() -> None:
    llm = FallbackLLM(primary=StubLLM(error=ValueError("only provider")), secondary=None)

    with pytest.raises(ValueError, match="only provider"):
        _generate(llm)


def test_nesting_chains_three_providers_in_order() -> None:
    """agent_run nests FallbackLLM inside itself; prove the third provider is reached."""
    first = StubLLM(error=RuntimeError("first down"))
    second = StubLLM(error=RuntimeError("second down"))
    third = StubLLM(value="third")

    chain = FallbackLLM(
        primary=first,
        secondary=FallbackLLM(primary=second, secondary=third),
    )

    assert _generate(chain).value == "third"
    assert first.calls == 1
    assert second.calls == 1
    assert third.calls == 1


def test_nesting_stops_at_the_first_provider_that_answers() -> None:
    second = StubLLM(value="second")
    third = StubLLM(value="third")

    chain = FallbackLLM(
        primary=StubLLM(error=RuntimeError("first down")),
        secondary=FallbackLLM(primary=second, secondary=third),
    )

    assert _generate(chain).value == "second"
    assert third.calls == 0


def test_records_the_model_that_actually_answered() -> None:
    class Named(StubLLM):
        def __init__(self, model: str, **kw: object) -> None:
            super().__init__(**kw)  # type: ignore[arg-type]
            self._model = model

    chain = FallbackLLM(
        primary=Named("model-a", error=RuntimeError("down")),
        secondary=FallbackLLM(
            primary=Named("model-b", error=RuntimeError("down")),
            secondary=Named("model-c", value="ok"),
        ),
    )

    _generate(chain)

    assert chain.last_model == "model-c"
