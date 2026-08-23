from __future__ import annotations

from typing import Any

from superbot_api.models.gateway import CompletionRequest, CompletionResponse, TokenUsage


def build_request_body(
    model_id: str, request: CompletionRequest, *, provider: str
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model_id,
        "messages": request.messages,
        "stream": False,
    }
    if request.tools:
        body["tools"] = request.tools
        body["tool_choice"] = request.tool_choice
    if request.temperature is not None:
        body["temperature"] = request.temperature
    if request.max_output_tokens is not None:
        body["max_tokens"] = request.max_output_tokens
    if provider == "dashscope" and request.enable_thinking is not None:
        body["enable_thinking"] = request.enable_thinking
    return body


def parse_response(payload: dict[str, Any], *, model_id: str) -> CompletionResponse:
    try:
        message = payload["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError("provider response did not contain a completion message") from error
    usage = payload.get("usage") or {}
    return CompletionResponse(
        model_id=model_id,
        content=message.get("content") or "",
        tool_calls=message.get("tool_calls") or [],
        provider_request_id=payload.get("id"),
        usage=TokenUsage(
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            cached_tokens=int(usage.get("prompt_cache_hit_tokens", 0)),
        ),
    )
