from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, Field
from superbot_api.domain.enums import ToolDecision
from superbot_api.models.gateway import (
    CompletionRequest,
    CompletionResponse,
    TokenUsage,
)
from superbot_api.policy.engine import PolicyEngine, ToolInvocation

from superbot_worker.agent.context import tool_descriptors_to_openai
from superbot_worker.tools.base import ToolRegistry


class CompletionModel(Protocol):
    async def complete(
        self,
        model_id: str,
        request: CompletionRequest,
        *,
        fallback_model_ids: Sequence[str] = (),
    ) -> CompletionResponse: ...


class AgentCancelled(RuntimeError):
    pass


class MaxStepsExceeded(RuntimeError):
    pass


class ApprovalRequired(RuntimeError):
    def __init__(
        self,
        tool_name: str,
        arguments: dict,
        checkpoint: dict[str, Any],
    ) -> None:
        super().__init__(f"approval required for {tool_name}")
        self.tool_name = tool_name
        self.arguments = arguments
        self.checkpoint = checkpoint


class AgentRunResult(BaseModel):
    content: str
    steps: int
    usage: TokenUsage = Field(default_factory=TokenUsage)


class AgentRuntime:
    def __init__(
        self,
        *,
        model: CompletionModel,
        tools: ToolRegistry,
        policy: PolicyEngine,
        model_id: str,
        bot_id: UUID | str,
        max_steps: int,
        is_cancelled: Callable[[], bool],
        fallback_model_ids: Sequence[str] = (),
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least one")
        self.model = model
        self.tools = tools
        self.policy = policy
        self.model_id = model_id
        self.bot_id = UUID(str(bot_id))
        self.max_steps = max_steps
        self.is_cancelled = is_cancelled
        self.fallback_model_ids = fallback_model_ids

    async def run(self, user_text: str) -> AgentRunResult:
        messages: list[dict[str, Any]] = [{"role": "user", "content": user_text}]
        usage = TokenUsage()

        for step in range(1, self.max_steps + 1):
            self._raise_if_cancelled()
            response = await self.model.complete(
                self.model_id,
                CompletionRequest(
                    messages=messages,
                    tools=tool_descriptors_to_openai(self.tools.descriptors()),
                ),
                fallback_model_ids=self.fallback_model_ids,
            )
            usage = TokenUsage(
                input_tokens=usage.input_tokens + response.usage.input_tokens,
                output_tokens=usage.output_tokens + response.usage.output_tokens,
                cached_tokens=usage.cached_tokens + response.usage.cached_tokens,
            )

            if not response.tool_calls:
                return AgentRunResult(content=response.content, steps=step, usage=usage)
            if step >= self.max_steps:
                raise MaxStepsExceeded(f"agent exceeded hard limit of {self.max_steps} steps")

            messages.append(
                {
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": response.tool_calls,
                }
            )
            for call in response.tool_calls:
                self._raise_if_cancelled()
                name, arguments = self._parse_tool_call(call)
                tool = self.tools.get(name)
                decision = self.policy.evaluate(
                    ToolInvocation(
                        bot_id=self.bot_id,
                        tool_name=name,
                        risk=tool.descriptor.risk,
                        arguments=arguments,
                    )
                )
                if decision.decision is ToolDecision.REQUIRE_APPROVAL:
                    raise ApprovalRequired(
                        name,
                        arguments,
                        {
                            "step": step,
                            "messages": messages,
                            "tool_call": call,
                            "reason": decision.reason,
                        },
                    )
                if decision.decision is ToolDecision.DENY:
                    content = f"denied by policy: {decision.reason}"
                else:
                    result = await self.tools.execute(name, arguments)
                    content = result.content
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": str(call.get("id", "")),
                        "name": name,
                        "content": content,
                    }
                )

        raise MaxStepsExceeded(f"agent exceeded hard limit of {self.max_steps} steps")

    def _raise_if_cancelled(self) -> None:
        if self.is_cancelled():
            raise AgentCancelled("agent task was cancelled")

    @staticmethod
    def _parse_tool_call(call: dict[str, Any]) -> tuple[str, dict]:
        function = call.get("function")
        if not isinstance(function, dict) or not isinstance(function.get("name"), str):
            raise ValueError("model returned an invalid tool call")
        raw_arguments = function.get("arguments", "{}")
        arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
        if not isinstance(arguments, dict):
            raise ValueError("tool arguments must be a JSON object")
        return function["name"], arguments
