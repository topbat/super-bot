from __future__ import annotations

from pydantic import BaseModel

from superbot_api.domain.models import ModelCapability


class CapabilityError(ValueError):
    pass


class ModelRequirement(BaseModel):
    text: bool = True
    vision: bool = False
    tool_calling: bool = False
    structured_output: bool = False
    thinking: bool = False
    streaming: bool = False
    minimum_context_window: int = 0


def validate_capability(capability: ModelCapability, requirement: ModelRequirement) -> None:
    checks = {
        "text": requirement.text,
        "vision": requirement.vision,
        "tool_calling": requirement.tool_calling,
        "structured_output": requirement.structured_output,
        "thinking": requirement.thinking,
        "streaming": requirement.streaming,
    }
    missing = [name for name, needed in checks.items() if needed and not getattr(capability, name)]
    if requirement.minimum_context_window > capability.context_window:
        missing.append(f"context_window>={requirement.minimum_context_window}")
    if missing:
        raise CapabilityError(f"model does not support required capabilities: {', '.join(missing)}")
