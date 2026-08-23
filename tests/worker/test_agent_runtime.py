from __future__ import annotations

from collections.abc import Callable

import pytest
from superbot_api.domain.enums import RiskLevel, ToolDecision
from superbot_api.domain.models import ToolDescriptor
from superbot_api.models.gateway import CompletionResponse, ModelUnavailable, TokenUsage
from superbot_api.policy.engine import PolicyEngine, PolicyRule
from superbot_worker.agent.runtime import (
    AgentCancelled,
    AgentRuntime,
    ApprovalRequired,
    MaxStepsExceeded,
)
from superbot_worker.tools.base import ToolRegistry, ToolResult


class EchoTool:
    descriptor = ToolDescriptor(
        name="utility.echo",
        description="Return supplied text",
        risk=RiskLevel.READ,
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    )

    async def execute(self, arguments: dict) -> ToolResult:
        return ToolResult(ok=True, content=arguments["text"])


class ScriptedModel:
    def __init__(self, responses: list[CompletionResponse | Exception]) -> None:
        self.responses = responses
        self.requests = []

    async def complete(self, model_id, request, *, fallback_model_ids=()):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def tool_call(name: str, arguments: str) -> CompletionResponse:
    return CompletionResponse(
        model_id="qwen3.7-plus",
        content="",
        tool_calls=[
            {
                "id": "call-1",
                "type": "function",
                "function": {"name": name, "arguments": arguments},
            }
        ],
        usage=TokenUsage(input_tokens=10, output_tokens=4),
    )


def final(content: str) -> CompletionResponse:
    return CompletionResponse(
        model_id="qwen3.7-plus",
        content=content,
        usage=TokenUsage(input_tokens=8, output_tokens=3),
    )


def runtime(
    model: ScriptedModel,
    *,
    rules: list[PolicyRule] | None = None,
    cancelled: Callable[[], bool] = lambda: False,
    max_steps: int = 8,
) -> AgentRuntime:
    registry = ToolRegistry()
    registry.register(EchoTool())
    return AgentRuntime(
        model=model,
        tools=registry,
        policy=PolicyEngine(rules or []),
        model_id="qwen3.7-plus",
        bot_id="00000000-0000-0000-0000-000000000001",
        max_steps=max_steps,
        is_cancelled=cancelled,
    )


async def test_agent_executes_tool_then_returns_final_answer() -> None:
    model = ScriptedModel([tool_call("utility.echo", '{"text":"hello"}'), final("done")])

    result = await runtime(model).run("echo a greeting")

    assert result.content == "done"
    assert result.steps == 2
    assert result.usage.input_tokens == 18
    assert model.requests[1].messages[-1]["content"] == "hello"


async def test_denied_tool_is_reported_to_model_without_execution() -> None:
    model = ScriptedModel([tool_call("utility.echo", '{"text":"secret"}'), final("stopped")])
    rules = [PolicyRule(effect=ToolDecision.DENY, tool_pattern="utility.echo")]

    result = await runtime(model, rules=rules).run("echo secret")

    assert result.content == "stopped"
    assert "denied" in model.requests[1].messages[-1]["content"]


async def test_approval_pauses_with_checkpoint() -> None:
    model = ScriptedModel([tool_call("utility.echo", '{"text":"needs review"}')])
    rules = [PolicyRule(effect=ToolDecision.REQUIRE_APPROVAL, tool_pattern="utility.echo")]

    with pytest.raises(ApprovalRequired) as caught:
        await runtime(model, rules=rules).run("echo after review")

    assert caught.value.tool_name == "utility.echo"
    assert caught.value.arguments == {"text": "needs review"}
    assert caught.value.checkpoint["step"] == 1


async def test_cancellation_stops_before_model_call() -> None:
    model = ScriptedModel([final("must not run")])

    with pytest.raises(AgentCancelled):
        await runtime(model, cancelled=lambda: True).run("stop")

    assert model.requests == []


async def test_max_steps_is_a_hard_limit() -> None:
    model = ScriptedModel([tool_call("utility.echo", "{}")])

    with pytest.raises(MaxStepsExceeded):
        await runtime(model, max_steps=1).run("loop")


async def test_provider_failure_is_not_hidden() -> None:
    model = ScriptedModel([ModelUnavailable("qwen is unavailable")])

    with pytest.raises(ModelUnavailable, match="qwen is unavailable"):
        await runtime(model).run("work")
