from __future__ import annotations

from collections.abc import Awaitable, Callable

from superbot_api.domain.models import ToolDescriptor

from superbot_worker.tools.base import ToolResult


class McpToolAdapter:
    """Adapt an injected MCP caller without placing credentials in the agent loop."""

    def __init__(
        self,
        descriptor: ToolDescriptor,
        caller: Callable[[dict], Awaitable[ToolResult]],
    ) -> None:
        self.descriptor = descriptor
        self._caller = caller

    async def execute(self, arguments: dict) -> ToolResult:
        return await self._caller(arguments)
