from __future__ import annotations

import json

import httpx
import pytest
from superbot_api.models.catalog import built_in_catalog
from superbot_api.models.gateway import (
    CompletionRequest,
    ModelGateway,
    ModelUnavailable,
    ProviderConfig,
)


class StaticSecrets:
    async def resolve(self, secret_ref: str | None) -> str | None:
        return "test-key" if secret_ref else None


def response_json(content: str = "done") -> dict:
    return {
        "id": "request-1",
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16},
    }


async def test_gateway_sends_qwen_thinking_extensions() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=response_json())

    providers = {
        "dashscope": ProviderConfig(
            name="dashscope",
            base_url="https://dashscope.invalid/compatible-mode/v1",
            secret_ref="env:DASHSCOPE_API_KEY",
        )
    }
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = ModelGateway(built_in_catalog(), providers, StaticSecrets(), client=client)
        result = await gateway.complete(
            "qwen3.7-plus",
            CompletionRequest(
                messages=[{"role": "user", "content": "inspect this screen"}],
                enable_thinking=True,
            ),
        )

    body = json.loads(captured[0].content)
    assert captured[0].url.path.endswith("/chat/completions")
    assert body["model"] == "qwen3.7-plus"
    assert body["enable_thinking"] is True
    assert result.content == "done"
    assert result.usage.input_tokens == 12


async def test_gateway_never_falls_back_without_explicit_chain() -> None:
    requested_models: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_models.append(json.loads(request.content)["model"])
        return httpx.Response(503, json={"error": {"message": "temporarily unavailable"}})

    providers = {
        "dashscope": ProviderConfig(
            name="dashscope",
            base_url="https://dashscope.invalid/v1",
            secret_ref="env:DASHSCOPE_API_KEY",
        )
    }
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = ModelGateway(built_in_catalog(), providers, StaticSecrets(), client=client)
        with pytest.raises(ModelUnavailable, match="qwen3.7-plus"):
            await gateway.complete(
                "qwen3.7-plus", CompletionRequest(messages=[{"role": "user", "content": "go"}])
            )

    assert requested_models == ["qwen3.7-plus"]


async def test_explicit_fallback_is_visible_in_result() -> None:
    requested_models: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        model = json.loads(request.content)["model"]
        requested_models.append(model)
        if model == "qwen3.7-plus":
            return httpx.Response(503, json={"error": {"message": "down"}})
        return httpx.Response(200, json=response_json("fallback result"))

    providers = {
        "dashscope": ProviderConfig(
            name="dashscope", base_url="https://dashscope.invalid/v1", secret_ref="env:KEY"
        )
    }
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = ModelGateway(built_in_catalog(), providers, StaticSecrets(), client=client)
        result = await gateway.complete(
            "qwen3.7-plus",
            CompletionRequest(messages=[{"role": "user", "content": "go"}]),
            fallback_model_ids=["qwen3.7-flash"],
        )

    assert requested_models == ["qwen3.7-plus", "qwen3.7-flash"]
    assert result.model_id == "qwen3.7-flash"
    assert result.fallback_from == "qwen3.7-plus"
