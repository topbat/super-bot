from __future__ import annotations

from pathlib import Path

from superbot_api.domain.enums import RiskLevel
from superbot_api.domain.models import ToolDescriptor

from superbot_worker.tools.base import ToolResult


class WorkspaceViolation(PermissionError):
    pass


class _WorkspaceTool:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def resolve_path(self, relative_path: str) -> Path:
        supplied = Path(relative_path)
        if supplied.is_absolute():
            raise WorkspaceViolation("absolute paths are not allowed")
        candidate = (self.workspace / supplied).resolve()
        if not candidate.is_relative_to(self.workspace):
            raise WorkspaceViolation("path escapes the bot workspace")
        return candidate


class FileReadTool(_WorkspaceTool):
    descriptor = ToolDescriptor(
        name="files.read",
        description="Read a UTF-8 text file inside the bot workspace",
        risk=RiskLevel.READ,
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    )

    async def execute(self, arguments: dict) -> ToolResult:
        path = self.resolve_path(str(arguments["path"]))
        content = path.read_text(encoding="utf-8")
        return ToolResult(
            ok=True,
            content=content,
            metadata={
                "path": path.relative_to(self.workspace).as_posix(),
                "size_bytes": path.stat().st_size,
            },
        )


class FileWriteTool(_WorkspaceTool):
    descriptor = ToolDescriptor(
        name="files.write",
        description="Write a UTF-8 text file inside the bot workspace",
        risk=RiskLevel.WRITE,
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    )

    async def execute(self, arguments: dict) -> ToolResult:
        relative_path = str(arguments["path"])
        content = str(arguments["content"])
        path = self.resolve_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolResult(
            ok=True,
            content=f"wrote {Path(relative_path).as_posix()}",
            metadata={
                "path": path.relative_to(self.workspace).as_posix(),
                "size_bytes": len(content.encode("utf-8")),
            },
        )
