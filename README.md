# Super Bot

Super Bot 是一个 Windows 优先、MIT 许可的持久化 AI 同事平台。它把聊天、长期 Bot、显式多模型路由、后台任务、审批、技能、定时例程、审计事件、产物和用量记录放在一个可自托管的桌面控制面中。

本项目不是 Grok Bot 的代码复制品，也不使用其品牌或私有实现；它根据公开产品行为重新设计了开放实现。公开文档显示，Grok Bot 的关键差异在于持久化具名 Bot、共享云计算机、工具/网站操作、多 Bot 协作、审批、技能与后台例程。Super Bot 保留这些产品原则，同时把模型、数据和部署控制权交给用户。

## 当前实现

- Windows x64 Electron 桌面端，Fluent UI，亮/暗主题，Bot、会话、任务时间线、审批、模型、例程、审计和 Worker 视图。
- FastAPI 控制面，PostgreSQL 持久化，SSE 事件回放与 `Last-Event-ID` 断线续传。
- 可恢复任务、租约、审批检查点、取消、硬步数/预算边界、父子任务委派和幂等键。
- 文件与 HTTP 工具、MCP 适配边界、工作区路径隔离、私网/元数据地址阻断。
- 技能版本哈希、IANA 时区 Cron 例程、真实 Scheduler 派发、Worker 心跳。
- Qwen 3.7、DeepSeek、Kimi、GLM、MiniMax、SiliconFlow、Ollama；只有显式配置的 fallback 才会回退。
- 产物写入 S3 兼容存储并记录 SHA-256，模型 token 用量写入数据库。
- Docker Compose：PostgreSQL、Valkey、SeaweedFS、API、Worker、Scheduler，以及可选的远程 Playwright Server + Browser Gateway profile。
- 交互浏览器：远程截图、坐标点击、键盘输入、按键、滚动、导航历史、会话关闭、私网阻断和脱敏动作审计。
- NSIS Windows 安装器；Electron 开启 context isolation、sandbox，关闭 node integration。

浏览器模块使用与 Python 客户端严格匹配的 Playwright 1.61 远程协议。桌面端只访问 FastAPI，不直接暴露内部 Browser Gateway 或 Playwright WebSocket；浏览器 profile 默认关闭。

## 快速开始

要求：Windows 10/11 x64、PowerShell 7、Docker Desktop、Node.js 22+、pnpm 10.32+、uv。

```powershell
Copy-Item .env.example .env
# 编辑 .env：至少设置 POSTGRES_PASSWORD、S3_ACCESS_KEY、S3_SECRET_KEY，
# 再设置要实际使用的模型供应商 Key。
pnpm install --frozen-lockfile
uv sync --frozen
.\scripts\dev.ps1
```

只启动后端：

```powershell
.\scripts\dev.ps1 -NoDesktop
```

启用远程交互浏览器：

```powershell
docker compose --profile browser up -d playwright-server browser-worker
```

如果 Clash/TUN 的 Fake-IP DNS 把公开域名解析到 `198.18.0.0/15`，在确认该网段确由本机可信 DNS 代理接管后设置 `SUPERBOT_BROWSER_TRUSTED_DNS_PROXY_CIDRS=198.18.0.0/15`；默认留空更安全。

生成 Windows 安装器：

```powershell
.\scripts\build-windows.ps1
```

安装器输出到 `apps/desktop/release/`。生产部署、备份和故障恢复见 [Windows 部署](docs/windows.md)。

## 质量门禁

```powershell
uv run ruff check .
uv run pytest -q
pnpm lint
pnpm test --run
pnpm build
docker compose config --quiet
pnpm --filter '@superbot/desktop' package:win
```

## 文档

- [产品与系统设计](docs/plans/2026-08-23-super-bot-design.md)
- [实现计划](docs/plans/2026-08-23-super-bot-implementation.md)
- [系统架构](docs/architecture.md)
- [模型供应商](docs/model-providers.md)
- [安全边界](docs/security.md)
- [Windows 与容器部署](docs/windows.md)

## 许可证

[MIT](LICENSE)。依赖组件保持各自许可证；部署前应按组织策略复核第三方依赖与模型供应商条款。
