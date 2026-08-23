from __future__ import annotations

import pytest
from pydantic import ValidationError
from superbot_api.domain.enums import ExecutionMode, ProviderKind, RiskLevel
from superbot_api.domain.models import BotCreate, ModelCapability, ProviderCreate, ToolDescriptor


def test_bot_requires_an_operational_role() -> None:
    with pytest.raises(ValidationError):
        BotCreate(name="helper", role="", description="does anything")


def test_provider_never_accepts_inline_secret() -> None:
    with pytest.raises(ValidationError, match="secret_ref"):
        ProviderCreate(
            name="Qwen",
            kind=ProviderKind.DASHSCOPE,
            base_url="https://example.invalid/v1",
            secret_ref="sk-inline-secret",
        )


def test_model_capability_is_explicit() -> None:
    capability = ModelCapability(
        text=True,
        vision=True,
        tool_calling=True,
        structured_output=True,
        thinking=True,
        streaming=True,
        context_window=1_000_000,
        max_output_tokens=65_536,
    )
    assert capability.vision is True
    assert capability.context_window == 1_000_000


def test_tool_descriptor_carries_risk_and_schema() -> None:
    tool = ToolDescriptor(
        name="files.read",
        description="Read a workspace file",
        risk=RiskLevel.READ,
        input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
    )
    assert tool.risk is RiskLevel.READ
    assert tool.input_schema["type"] == "object"


def test_execution_mode_defaults_to_sandbox() -> None:
    bot = BotCreate(name="Researcher", role="research", description="Cite current sources")
    assert bot.execution_mode is ExecutionMode.SANDBOX
