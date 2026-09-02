"""Google AI Studio adapter for hosted Gemma models."""

import json
import time
from typing import Any

from pydantic import ValidationError

from alphabeater.llm.base import ResponseT


def _extract_json(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]).strip()
    return json.loads(cleaned)


class GemmaLLM:
    """Generate validated JSON; no model output is trusted before validation."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemma-4-26b-a4b-it",
        max_attempts: int = 3,
    ) -> None:
        try:
            from google import genai
            from google.genai import errors, types
        except ImportError as exc:  # pragma: no cover - depends on optional runtime setup
            raise RuntimeError("Install the project dependencies to use Gemma") from exc

        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=60_000),
        )
        self._api_error = errors.APIError
        self._generation_config = types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL),
        )
        self._model = model
        self._max_attempts = max_attempts

    def generate(
        self,
        *,
        response_type: type[ResponseT],
        system_prompt: str,
        user_prompt: str,
    ) -> ResponseT:
        schema = json.dumps(response_type.model_json_schema(), separators=(",", ":"))
        prompt = (
            f"{system_prompt}\n\n"
            "Return exactly one JSON value matching this JSON Schema. "
            "Do not use markdown fences or add commentary.\n"
            f"SCHEMA: {schema}\n\nTASK:\n{user_prompt}"
        )
        last_error: Exception | None = None
        for attempt in range(self._max_attempts):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=self._generation_config,
                )
                if not response.text:
                    raise ValueError("Gemma returned no text")
                return response_type.model_validate(_extract_json(response.text))
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = exc
                if attempt + 1 == self._max_attempts:
                    break
                prompt += (
                    "\n\nYour previous response did not match the schema. "
                    f"Validation error: {exc}. Return only corrected JSON."
                )
            except self._api_error as exc:
                last_error = exc
                code = getattr(exc, "code", None)
                if attempt + 1 == self._max_attempts or code not in {429, 500, 502, 503, 504}:
                    raise
                time.sleep(2**attempt)
        raise ValueError(f"Gemma returned invalid structured output: {last_error}")
