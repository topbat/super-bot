from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field
from superbot_api.domain.models import ToolDescriptor


class ToolResult(BaseModel):
    ok: bool
    content: str
    metadata: dict = Field(default_factory=dict)


class Tool(Protocol):
    descriptor: ToolDescriptor

    async def execute(self, arguments: dict) -> ToolResult: ...


class UnknownTool(LookupError):
    pass


class DuplicateTool(ValueError):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        name = tool.descriptor.name
        if name in self._tools:
            raise DuplicateTool(f"tool {name} is already registered")
        self._tools[name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as error:
            raise UnknownTool(f"tool {name} is not registered") from error

    def descriptors(self) -> list[ToolDescriptor]:
        return [tool.descriptor for tool in self._tools.values()]

    async def execute(self, name: str, arguments: dict) -> ToolResult:
        return await self.get(name).execute(arguments)
