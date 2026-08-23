from __future__ import annotations

import pytest
from superbot_api.models.capabilities import CapabilityError, ModelRequirement
from superbot_api.models.catalog import built_in_catalog


def test_catalog_prioritizes_domestic_agent_models() -> None:
    catalog = built_in_catalog()

    assert catalog.get("qwen3.7-plus").capability.context_window == 1_000_000
    assert catalog.get("qwen3.7-plus").capability.vision is True
    assert catalog.get("deepseek-chat").capability.tool_calling is True
    assert {model.provider for model in catalog.list()} >= {
        "dashscope",
        "deepseek",
        "moonshot",
        "zhipu",
        "minimax",
        "siliconflow",
        "ollama",
    }


def test_catalog_rejects_model_without_required_capability() -> None:
    catalog = built_in_catalog()

    with pytest.raises(CapabilityError, match="vision"):
        catalog.require("deepseek-chat", ModelRequirement(vision=True))


def test_unknown_model_is_not_silently_invented() -> None:
    catalog = built_in_catalog()

    with pytest.raises(KeyError, match="unknown-model"):
        catalog.get("unknown-model")
