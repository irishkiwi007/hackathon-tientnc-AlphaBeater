"""Route structured generation to a second provider when the first is unavailable.

The hosted primary model returns intermittent 503s under load. A run that dies there wastes a
market window, so the same prompt is retried against an independent provider. Both conform to
`StructuredLLM`, so nothing downstream knows which one answered.
"""

from alphabeater.llm.base import ResponseT, StructuredLLM


class FallbackLLM:
    """Try the primary provider, then the secondary. Records which one answered."""

    def __init__(self, *, primary: StructuredLLM, secondary: StructuredLLM | None) -> None:
        self._primary = primary
        self._secondary = secondary
        self.last_provider: str | None = None
        self.last_model: str | None = None
        self.fallback_count = 0

    @staticmethod
    def _model_of(provider: StructuredLLM) -> str | None:
        """Name the model that actually answered, seeing through a nested chain."""
        nested = getattr(provider, "last_model", None)
        if nested:
            return str(nested)
        model = getattr(provider, "_model", None)
        return str(model) if model else None

    def generate(
        self,
        *,
        response_type: type[ResponseT],
        system_prompt: str,
        user_prompt: str,
    ) -> ResponseT:
        try:
            result = self._primary.generate(
                response_type=response_type,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        except Exception as primary_error:
            if self._secondary is None:
                raise
            try:
                result = self._secondary.generate(
                    response_type=response_type,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                )
            except Exception as secondary_error:
                raise RuntimeError(
                    "both LLM providers failed; "
                    f"primary: {primary_error}; secondary: {secondary_error}"
                ) from secondary_error
            self.last_provider = "secondary"
            self.last_model = self._model_of(self._secondary)
            self.fallback_count += 1
            return result

        self.last_provider = "primary"
        self.last_model = self._model_of(self._primary)
        return result
