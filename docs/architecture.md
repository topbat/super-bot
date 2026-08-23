# 系统架构

## 设计目标

桌面端只负责交互与控制，任务状态由服务端持久化。关闭 PC 客户端不会撤销已提交任务；只要容器服务继续运行，Worker 和 Scheduler 就能继续推进。系统把“模型建议做什么”和“策略是否允许执行”分离，模型不能绕过确定性策略层。

## 组件

| 组件 | 职责 | 状态来源 |
| --- | --- | --- |
| Electron + React | Windows 控制面、会话、审批、监控 | FastAPI |
| FastAPI | 稳定 API、SSE、校验、Problem Details | PostgreSQL |
| Worker | 模型循环、工具执行、检查点、产物 | PostgreSQL + S3 |
| Scheduler | 扫描到期例程并幂等生成任务 | PostgreSQL |
| Browser Gateway | 远程 Playwright 会话句柄、策略路由、截图与交互动作 | 内存 + Playwright Server |
| Playwright Server | 隔离 Chromium 进程与 WebSocket 协议端点 | 临时浏览器上下文 |
| PostgreSQL | Bot、消息、任务、事件、审批、技能、例程、用量 | 唯一事实源 |
| Valkey | Redis Streams 兼容传输与协调 | 可重建传输层 |
| SeaweedFS | S3 兼容产物对象存储 | 命名卷 |

## 关键数据链路

1. 桌面端向 `POST /api/v1/bots/{id}/messages` 提交消息和幂等键。
2. API 在同一持久化域创建 Conversation、Message、Task 和 `created` 事件。
3. Worker 使用数据库租约认领任务，写入 `started`，调用明确选中的模型。
4. 模型请求工具时，策略返回 allow、require approval 或 deny。需要审批时，完整检查点写入 Task，租约释放。
5. 用户批准后任务重新排队；Worker 从原检查点精确执行待批工具，不重新生成另一组参数。
6. 每个工具、模型响应、产物、失败和完成状态都进入追加式事件流；桌面用 SSE 游标恢复。
7. 文件产物上传 S3，并在 PostgreSQL 保存媒体类型、大小、存储键和 SHA-256；用量单独保存 token 与供应商请求 ID。

浏览器链路独立于模型任务：Electron 调用 `/api/v1/browser`，API 先写入/读取 `browser_sessions`，再通过内部 HTTP 调用 Browser Gateway；Gateway 使用 `BrowserType.connect()` 连接同版本 Playwright Server。每个动作返回当前 URL、标题、视口、PNG 截图和可交互元素摘要，API 同步会话并把脱敏参数写入 `browser_actions`。Playwright Server 与 Gateway 都不发布宿主端口。

例程由 Scheduler 使用行锁和确定性 occurrence 幂等键派发。多 Bot 委派会创建带 `parent_task_id` 的子任务，并在父任务记录 `delegated` 事件。

## 一致性与恢复

- PostgreSQL 是权威状态；Valkey 丢失不能丢掉 Task。
- Task 用租约所有者与过期时间处理 Worker 崩溃。
- 每次外部提交和例程发生点都有稳定幂等键。
- 审批使用持久化 checkpoint；拒绝进入明确失败状态。
- SSE 事件带单调 ID，客户端用 `Last-Event-ID` 继续。
- 没有配置供应商 Key 时任务明确失败；不会静默换到其他模型。
- 浏览器 Context/页面句柄是临时执行状态；Gateway 重启后旧会话会明确失败，不伪装为已恢复。

## 扩展点

ToolRegistry 接受内置工具与 MCP adapter；模型层使用 OpenAI-compatible 协议并保留供应商特定参数入口。新增工具必须声明 JSON Schema 和风险级别；新增供应商必须定义能力、鉴权引用、请求映射和协议测试。
