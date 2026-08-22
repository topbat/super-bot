from __future__ import annotations

from superbot_api.models.gateway import ProviderConfig


def default_provider_configs() -> dict[str, ProviderConfig]:
    return {
        "dashscope": ProviderConfig(
            name="dashscope",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            secret_ref="env:DASHSCOPE_API_KEY",
        ),
        "deepseek": ProviderConfig(
            name="deepseek",
            base_url="https://api.deepseek.com/v1",
            secret_ref="env:DEEPSEEK_API_KEY",
        ),
        "moonshot": ProviderConfig(
            name="moonshot",
            base_url="https://api.moonshot.cn/v1",
            secret_ref="env:MOONSHOT_API_KEY",
        ),
        "zhipu": ProviderConfig(
            name="zhipu",
            base_url="https://open.bigmodel.cn/api/paas/v4",
            secret_ref="env:ZHIPU_API_KEY",
        ),
        "minimax": ProviderConfig(
            name="minimax",
            base_url="https://api.minimax.chat/v1",
            secret_ref="env:MINIMAX_API_KEY",
        ),
        "siliconflow": ProviderConfig(
            name="siliconflow",
            base_url="https://api.siliconflow.cn/v1",
            secret_ref="env:SILICONFLOW_API_KEY",
        ),
        "ollama": ProviderConfig(
            name="ollama", base_url="http://host.docker.internal:11434/v1", secret_ref=None
        ),
    }

