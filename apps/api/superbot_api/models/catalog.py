from __future__ import annotations

from pydantic import BaseModel, Field

from superbot_api.domain.models import ModelCapability
from superbot_api.models.capabilities import ModelRequirement, validate_capability


class ModelSpec(BaseModel):
    id: str
    display_name: str
    provider: str
    capability: ModelCapability
    default_parameters: dict = Field(default_factory=dict)


class ModelCatalog:
    def __init__(self, models: list[ModelSpec]) -> None:
        self._models = {model.id: model for model in models}

    def get(self, model_id: str) -> ModelSpec:
        try:
            return self._models[model_id]
        except KeyError as error:
            raise KeyError(f"unknown model: {model_id}") from error

    def list(self) -> list[ModelSpec]:
        return list(self._models.values())

    def require(self, model_id: str, requirement: ModelRequirement) -> ModelSpec:
        model = self.get(model_id)
        validate_capability(model.capability, requirement)
        return model


def _capability(
    *,
    vision: bool = False,
    structured: bool = False,
    thinking: bool = True,
    context: int = 1_000_000,
) -> ModelCapability:
    return ModelCapability(
        text=True,
        vision=vision,
        tool_calling=True,
        structured_output=structured,
        thinking=thinking,
        streaming=True,
        context_window=context,
        max_output_tokens=65_536,
    )


def built_in_catalog() -> ModelCatalog:
    models = [
        ModelSpec(
            id="qwen3.7-max",
            display_name="Qwen 3.7 Max",
            provider="dashscope",
            capability=_capability(vision=True, structured=True),
        ),
        ModelSpec(
            id="qwen3.7-plus",
            display_name="Qwen 3.7 Plus",
            provider="dashscope",
            capability=_capability(vision=True, structured=True),
        ),
        ModelSpec(
            id="qwen3.7-flash",
            display_name="Qwen 3.7 Flash",
            provider="dashscope",
            capability=_capability(vision=True, structured=True),
        ),
        ModelSpec(
            id="deepseek-chat",
            display_name="DeepSeek Chat",
            provider="deepseek",
            capability=_capability(context=128_000, thinking=False),
        ),
        ModelSpec(
            id="deepseek-reasoner",
            display_name="DeepSeek Reasoner",
            provider="deepseek",
            capability=_capability(context=128_000),
        ),
        ModelSpec(
            id="kimi-k2.7-code",
            display_name="Kimi K2.7 Code",
            provider="moonshot",
            capability=_capability(context=256_000),
        ),
        ModelSpec(
            id="glm-5.2",
            display_name="GLM 5.2",
            provider="zhipu",
            capability=_capability(structured=True),
        ),
        ModelSpec(
            id="MiniMax-M3",
            display_name="MiniMax M3",
            provider="minimax",
            capability=_capability(context=192_000),
        ),
        ModelSpec(
            id="siliconflow-default",
            display_name="SiliconFlow Custom Model",
            provider="siliconflow",
            capability=_capability(context=128_000),
        ),
        ModelSpec(
            id="ollama-local",
            display_name="Ollama Local Model",
            provider="ollama",
            capability=_capability(context=128_000, thinking=False),
        ),
    ]
    return ModelCatalog(models)

