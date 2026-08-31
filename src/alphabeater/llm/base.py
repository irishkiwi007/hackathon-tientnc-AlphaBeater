"""Provider-neutral structured generation interface."""

from typing import Protocol, TypeVar

from pydantic import BaseModel

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class StructuredLLM(Protocol):
    def generate(
        self,
        *,
        response_type: type[ResponseT],
        system_prompt: str,
        user_prompt: str,
    ) -> ResponseT: ...

