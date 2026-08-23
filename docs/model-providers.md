# 模型供应商

## 路由原则

每个 Task 固定一个 `model_id`。只有 Bot 明确设置 `fallback_model_ids` 时才按顺序尝试回退；未配置 Key、网络错误、HTTP 错误和协议错误都会显式进入失败/审计链路。系统不会因为某个国内模型不可用而悄悄切换到另一家供应商。

## 内置目录

| Provider | 内置模型标识 | 环境变量 |
| --- | --- | --- |
| 阿里云百炼 DashScope | `qwen3.7-max`、`qwen3.7-plus`、`qwen3.7-flash` | `SUPERBOT_DASHSCOPE_API_KEY` |
| DeepSeek | `deepseek-chat`、`deepseek-reasoner` | `SUPERBOT_DEEPSEEK_API_KEY` |
| Moonshot/Kimi | `kimi-k2.7-code` | `SUPERBOT_MOONSHOT_API_KEY` |
| 智谱 GLM | `glm-5.2` | `SUPERBOT_ZHIPU_API_KEY` |
| MiniMax | `MiniMax-M3` | `SUPERBOT_MINIMAX_API_KEY` |
| SiliconFlow | `siliconflow-default` | `SUPERBOT_SILICONFLOW_API_KEY` |
| Ollama | `ollama-local` | 无；默认访问 `host.docker.internal:11434/v1` |

模型名称和能力会随供应商发布变化。上线前应在供应商控制台确认账户实际可用的模型 ID；目录声明不等于账号已获权限。若供应商实际 ID 不同，应在 catalog 中增加独立映射并补请求合同测试，不要靠静默别名猜测。

## 配置

复制 `.env.example` 为 `.env`，只填写要用的 Key。Compose 会把这些值仅注入应用容器；API 响应、事件和错误会避免输出 Key。

Ollama 在 Windows Docker Desktop 中通过 `host.docker.internal` 访问宿主机。先在宿主启动兼容 OpenAI 的 Ollama 接口，并确保拉取的模型与 catalog 映射一致。

## 新增兼容供应商

1. 在 `default_provider_configs()` 增加 base URL 和外部 secret reference。
2. 在 catalog 增加稳定的产品 ID、供应商实际模型 ID 与能力元数据。
3. 在请求构建器中增加必要的供应商特定字段。
4. 添加无网络合同测试，覆盖请求体、工具调用、usage 和错误净化。
5. 将 Key 作为可选 Compose 环境变量传入，绝不写入镜像或数据库明文。
