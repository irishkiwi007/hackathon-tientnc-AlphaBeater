import httpx
import pytest
from pydantic import BaseModel

from alphabeater.llm.featherless import FeatherlessLLM


class Reply(BaseModel):
    value: str


def _client(handler: object) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="https://example.invalid")


def _completion(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def _generate(llm: FeatherlessLLM) -> Reply:
    return llm.generate(response_type=Reply, system_prompt="sys", user_prompt="user")


def test_parses_a_valid_json_reply() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _completion('{"value": "hello"}')

    llm = FeatherlessLLM(api_key="k", model="m", client=_client(handler))

    assert _generate(llm).value == "hello"


def test_strips_markdown_fences() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _completion('```json\n{"value": "fenced"}\n```')

    llm = FeatherlessLLM(api_key="k", model="m", client=_client(handler))

    assert _generate(llm).value == "fenced"


def test_sends_bearer_token_and_model() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        seen["url"] = str(request.url)
        return _completion('{"value": "ok"}')

    _generate(FeatherlessLLM(api_key="secret-key", model="some/model", client=_client(handler)))

    assert seen["auth"] == "Bearer secret-key"
    assert str(seen["url"]).endswith("/chat/completions")


def test_retries_a_503_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={"error": "busy"})
        return _completion('{"value": "second try"}')

    llm = FeatherlessLLM(api_key="k", model="m", client=_client(handler), retry_delay=0.0)

    assert _generate(llm).value == "second try"
    assert calls["n"] == 2


def test_gives_up_after_max_attempts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "busy"})

    llm = FeatherlessLLM(
        api_key="k", model="m", client=_client(handler), max_attempts=2, retry_delay=0.0
    )

    with pytest.raises(RuntimeError, match="Featherless"):
        _generate(llm)


def test_does_not_retry_an_authentication_error() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(401, json={"error": "bad key"})

    llm = FeatherlessLLM(api_key="k", model="m", client=_client(handler), retry_delay=0.0)

    with pytest.raises(RuntimeError):
        _generate(llm)
    assert calls["n"] == 1


def test_retries_when_the_model_returns_unparseable_text() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return _completion("not json at all")
        return _completion('{"value": "recovered"}')

    llm = FeatherlessLLM(api_key="k", model="m", client=_client(handler), retry_delay=0.0)

    assert _generate(llm).value == "recovered"


def test_rejects_a_reply_that_violates_the_schema() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _completion('{"wrong_field": 1}')

    llm = FeatherlessLLM(
        api_key="k", model="m", client=_client(handler), max_attempts=1, retry_delay=0.0
    )

    with pytest.raises(ValueError):
        _generate(llm)
