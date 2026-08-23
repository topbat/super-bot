from __future__ import annotations

from pathlib import Path

import pytest
from superbot_api.domain.enums import RiskLevel
from superbot_worker.tools.base import ToolRegistry, ToolResult
from superbot_worker.tools.files import FileReadTool, FileWriteTool, WorkspaceViolation
from superbot_worker.tools.http import HttpReadTool, UnsafeNetworkTarget


async def test_registry_executes_a_registered_tool() -> None:
    registry = ToolRegistry()
    registry.register(FileReadTool(Path(__file__).parent))

    result = await registry.execute("files.read", {"path": "test_tool_registry.py"})

    assert result.ok is True
    assert "test_registry_executes" in result.content
    assert registry.descriptors()[0].risk is RiskLevel.READ


async def test_file_tool_rejects_workspace_escape(tmp_path: Path) -> None:
    tool = FileWriteTool(tmp_path)

    with pytest.raises(WorkspaceViolation):
        await tool.execute({"path": "../outside.txt", "content": "blocked"})


async def test_file_write_returns_reviewable_metadata(tmp_path: Path) -> None:
    tool = FileWriteTool(tmp_path)

    result = await tool.execute({"path": "reports/result.txt", "content": "verified"})

    assert result == ToolResult(
        ok=True,
        content="wrote reports/result.txt",
        metadata={"path": "reports/result.txt", "size_bytes": 8},
    )
    assert (tmp_path / "reports" / "result.txt").read_text(encoding="utf-8") == "verified"


@pytest.mark.parametrize("url", ["http://127.0.0.1/admin", "http://169.254.169.254/latest"])
async def test_http_tool_blocks_private_and_metadata_targets(url: str) -> None:
    with pytest.raises(UnsafeNetworkTarget):
        await HttpReadTool().execute({"url": url})
