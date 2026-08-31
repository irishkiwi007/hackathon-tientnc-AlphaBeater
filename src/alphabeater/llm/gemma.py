"""Google AI Studio adapter for hosted Gemma models."""

import json
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

    def __init__(self, *, api_key: str, model: str = "gemma-4-26b-a4b-it") -> None:
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover - depends on optional runtime setup
            raise RuntimeError("Install the project dependencies to use Gemma") from exc

        self._client = genai.Client(api_key=api_key)
        self._model = model

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
        response = self._client.models.generate_content(model=self._model, contents=prompt)
        if not response.text:
            raise RuntimeError("Gemma returned no text")
        try:
            return response_type.model_validate(_extract_json(response.text))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError("Gemma returned invalid structured output") from exc
