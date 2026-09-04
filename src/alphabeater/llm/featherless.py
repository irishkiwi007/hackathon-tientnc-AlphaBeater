"""Featherless AI adapter for hosted open-source models.

Featherless exposes an OpenAI-compatible chat-completions endpoint. This adapter exists so the
research layer is not tied to a single provider: when the primary model is unavailable, the same
prompts can be answered by an independent one. See `FallbackLLM`.
"""

import json
import time

from pydantic import ValidationError

from alphabeater.llm._json import extract_json
from alphabeater.llm.base import ResponseT

BASE_URL = "https://api.featherless.ai/v1"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V3.1"

_RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})


class FeatherlessLLM:
    """Generate validated JSON; no model output is trusted before validation."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_MODEL,
        client: object | None = None,
        max_attempts: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 60.0,
    ) -> None:
        import httpx

        self._httpx = httpx
        self._model = model
        self._max_attempts = max_attempts
        self._retry_delay = retry_delay
        self._client = client or httpx.Client(base_url=BASE_URL, timeout=timeout)
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def generate(
        self,
        *,
        response_type: type[ResponseT],
        system_prompt: str,
        user_prompt: str,
    ) -> ResponseT:
        schema = json.dumps(response_type.model_json_schema(), separators=(",", ":"))
        instruction = (
            "Return exactly one JSON value matching this JSON Schema. "
            "Do not use markdown fences or add commentary.\n"
            f"SCHEMA: {schema}"
        )
        prompt = f"{instruction}\n\nTASK:\n{user_prompt}"
        last_error: Exception | None = None

        for attempt in range(self._max_attempts):
            try:
                text = self._complete(system_prompt, prompt)
                return response_type.model_validate(extract_json(text))
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = exc
                if attempt + 1 == self._max_attempts:
                    break
                prompt += (
                    "\n\nYour previous response did not match the schema. "
                    f"Validation error: {exc}. Return only corrected JSON."
                )
            except self._httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                if attempt + 1 == self._max_attempts or status not in _RETRYABLE_STATUS:
                    raise RuntimeError(f"Featherless request failed: {status}") from exc
                time.sleep(self._retry_delay * (2**attempt))
            except self._httpx.HTTPError as exc:
                last_error = exc
                if attempt + 1 == self._max_attempts:
                    raise RuntimeError(f"Featherless request failed: {exc}") from exc
                time.sleep(self._retry_delay * (2**attempt))

        raise ValueError(f"Featherless returned invalid structured output: {last_error}")

    def _complete(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.post(
            "/chat/completions",
            headers=self._headers,
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
            },
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload.get("choices") or []
        if not choices:
            raise ValueError("Featherless returned no choices")
        content = choices[0].get("message", {}).get("content")
        if not content:
            raise ValueError("Featherless returned no text")
        return str(content)
