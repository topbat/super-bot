# Super Bot 产品与系统设计

## 1. 产品定义

Super Bot 是一个 MIT 协议的持久化 AI 同事平台。用户可以创建具有明确职责的 Bot，让其在本机、隔离容器或远程 Worker 中使用模型、浏览器、终端、文件和 MCP 工具完成真实工作。桌面应用是控制台，不是唯一执行位置。任务进入服务端控制面后可以在 Windows 客户端关闭时继续运行。

首发聚焦 Windows PC，同时保证后端与 Worker 可以通过 Docker Compose 部署到 Windows、Linux 服务器或云主机。默认允许个人在单机上完成安装、配置模型、创建 Bot、发起任务、查看过程、审批操作和管理定时例程。远程模式沿用同一套 API 与数据模型，不分裂为第二套产品。

核心产品承诺如下：

- Bot 是持久角色，不是一次性聊天会话。
- 模型由用户显式选择，失败时不得静默切换供应商。
- API、MCP、浏览器和终端都是统一 Tool Run，可被审计和审批。
- 每个任务都有状态机、事件流、成本记录、产物和可恢复检查点。
- 执行环境可以共享，也可以按 Bot 或任务使用独立容器。
- Skill 是开放文本规范，Routine 是可追踪、可暂停、可重试的持久任务。
- 所有高风险动作先经过确定性规则，再经过可选模型审查，最后进入人工审批。

## 2. 功能边界

### 2.1 首个完整版本必须具备

1. Bot 名册：创建、编辑、复制、归档、删除、头像、角色说明、默认模型、环境策略、预算与审批策略。
2. 对话与任务：流式消息、任务状态、停止、重试、附件、工具活动、结构化错误、结果产物。
3. 多 Bot 协作：显式委派、单一阶段负责人、父子任务、上下文摘要、共享产物。
4. 模型中心：供应商、模型、能力、上下文、费用、健康状态、密钥引用和连接测试。
5. 国内模型：阿里云百炼 Qwen 3.7、DeepSeek、Kimi、智谱 GLM、MiniMax、SiliconFlow，以及 Ollama 和任意 OpenAI 兼容接口。
6. Agent Runtime：推理循环、工具调用、最大步数、超时、取消、断点、错误分类和成本硬限制。
7. Tool Runtime：内置文件、只读系统信息、HTTP、浏览器和 MCP 工具，支持风险级别与审批。
8. Agent Computer：本机受限模式、Docker 隔离模式和远程 Worker 模式；浏览器执行基于 Playwright。
9. 审批中心：待审批队列、允许一次、拒绝、作用域允许规则、规则冲突时拒绝优先。
10. Skills：Markdown 与 YAML 前置元数据，支持导入、导出、版本和启停。
11. Routines：Cron、时区、手动测试、启停、运行历史、重试和幂等键。
12. 审计与成本：事件时间线、模型用量、工具参数摘要、审批、错误、产物校验值和预算告警。
13. Docker Compose：API、Worker、PostgreSQL、Valkey、SeaweedFS，可选择启用浏览器执行容器。
14. Windows 安装：Electron 桌面开发与打包脚本，支持连接本地或远程 API。

### 2.2 后续扩展但预留协议

- OAuth 连接器市场和团队单点登录。
- 录屏示教生成 Skill。
- WebRTC 实时桌面流和移动客户端。
- 多租户计费、组织管理、审计导出和策略模板。
- Kubernetes 执行池与硬件安全密钥转发。

## 3. 总体架构

```text
Windows Electron Desktop
  | REST + SSE
  v
FastAPI Control Plane
  |-- PostgreSQL: durable product state and audit events
  |-- Valkey: Redis-compatible short-lived coordination
  |-- SeaweedFS/S3: attachments, screenshots and generated artifacts
  |-- Model Gateway: explicit provider adapters and capability registry
  |-- Policy Engine: deterministic rules, budgets and approvals
  `-- Scheduler: durable routine dispatch
          |
          v
Agent Worker Pool
  |-- local process executor
  |-- Docker sandbox executor
  |-- remote registered worker
  `-- Playwright browser executor and MCP clients
```

桌面端不保存模型密钥。密钥进入服务端后由 Secret Store 接口保存。开发版使用服务端环境变量引用，Windows 单机增强版可以使用 Credential Manager，团队版可接入 Vault。数据库只保存 `secret_ref`，日志和模型上下文不得出现密钥明文。

控制面和 Worker 使用相同 Python 包中的领域协议。首版执行队列直接使用 PostgreSQL 行锁与租约，Valkey 提供 Redis Streams 兼容扩展点和短期协调；任务与事件的真实状态始终以 PostgreSQL 为准。Worker 领取租约后定期续租；租约过期的任务可恢复到上一个检查点。

## 4. 数据链路

### 4.1 用户消息到结果

1. 桌面端提交消息、附件引用、选定 Bot 和可选模型覆盖。
2. API 创建 Message、Task 和第一条 TaskEvent，事务提交后写入派发箱。
3. Worker 从 PostgreSQL 中以 `FOR UPDATE SKIP LOCKED` 领取到期租约；横向扩展时可启用 Valkey Streams 通知降低轮询延迟。
4. Worker 领取任务并加载 Bot 配置、相关记忆、Skill、审批策略和预算。
5. Model Gateway 根据显式模型 ID 调用对应供应商，不进行未授权降级。
6. 模型产生文本或 Tool Call。Policy Engine 先做参数级规则判断。
7. 低风险调用直接执行；中高风险调用创建 Approval 并暂停任务。
8. 用户审批后 Worker 从检查点继续，拒绝则把拒绝结果反馈给模型。
9. 每个步骤写 TaskEvent；截图与文件进入对象存储并写 Artifact 元数据。
10. Worker 生成结果、用量和记忆候选，任务进入 succeeded、failed 或 cancelled。
11. 桌面端通过 SSE 增量接收事件，断线重连使用事件游标补齐。

### 4.2 Routine 到后台任务

Scheduler 按时区计算 `next_run_at`，用数据库行锁领取到期 Routine。每次派发生成由 Routine ID 和计划时间组成的幂等键。相同键只能创建一个 Run。失败按照指数退避重试，超过上限进入 dead letter 状态，绝不复用陈旧输入伪装成功。

### 4.3 多 Bot 委派

委派被建模为父任务创建子任务，不是隐藏消息。父任务保存接收 Bot、目标、允许访问的上下文引用、截止时间和交付格式。每个阶段只有一个 owner。子任务结果以摘要和产物引用返回父任务，完整事件仍可独立审计。

## 5. 核心数据模型

- `bots`: 身份、角色、模型、环境、审批配置、状态。
- `conversations`: 单 Bot 或群组上下文。
- `conversation_members`: 用户与 Bot 成员关系。
- `messages`: 用户、Bot、系统和工具消息。
- `tasks`: durable 状态机、owner、parent、预算、租约、取消标记。
- `task_events`: append-only 事件流和 SSE 游标。
- `approvals`: 操作摘要、参数摘要、风险、决定和决定人。
- `artifacts`: 对象存储位置、媒体类型、大小、SHA-256、来源任务。
- `providers`: 供应商类型、基础地址、密钥引用和启用状态。
- `models`: 显式模型 ID、能力、上下文、费率和健康状态。
- `skills` 与 `skill_versions`: 开放格式技能及不可变版本。
- `routines` 与 `routine_runs`: 调度定义、幂等运行和历史。
- `tools`: 工具描述、JSON Schema、风险级别和启用策略。
- `usage_records`: 输入、输出、缓存、费用、供应商请求 ID。
- `memories`: 作用域、来源、置信度、有效期和可撤销状态。
- `workers`: 能力、状态、租约、区域和最后心跳。

## 6. 模型网关

模型注册表不把“OpenAI 兼容”误认为“能力完全相同”。每个模型记录：文本、视觉、工具调用、结构化输出、思考模式、上下文长度、最大输出、流式能力和定价。调用前根据任务要求进行能力校验。

首批适配器：

- `dashscope`: Qwen 3.7 Max、Plus、Flash，支持百炼 OpenAI 兼容端点和供应商扩展参数。
- `deepseek`: 官方 OpenAI 兼容接口。
- `moonshot`: Kimi。
- `zhipu`: GLM。
- `minimax`: MiniMax。
- `siliconflow`: 国内聚合接口。
- `ollama`: 本地模型。
- `openai_compatible`: 用户自定义基础地址和模型 ID。

默认推荐 `qwen3.7-plus` 处理综合 Agent 工作。模型不可用时任务明确失败，并给出可选模型建议。只有用户为某个 Bot 配置了按顺序排列的 fallback 列表时才允许切换，事件流必须记录切换原因。

## 7. 执行、安全与审批

工具风险分为四级：

- `read`: 只读查询，默认允许。
- `write`: 可恢复写入，按规则决定。
- `sensitive`: 外发消息、发布、权限变化、个人信息处理，默认审批。
- `critical`: 删除、付款、生产变更、凭证操作，始终审批且不能创建永久允许规则。

规则匹配对象包括 Bot、工具、动作、资源路径、域名和参数约束。拒绝规则高于允许规则，关键级别高于所有个人允许规则。浏览器下载、终端命令和 HTTP 请求必须经过统一策略层，不能绕过审计。

Docker Sandbox 默认使用非 root 用户、只读基础文件系统、临时工作目录、CPU/内存/PID 限额、禁用特权模式和受控网络。Windows 本机执行默认关闭；启用时每条命令都展示完整命令、工作目录和目标文件，并逐次审批。

## 8. PC 端信息架构与视觉

使用 Electron、React、TypeScript 和 Fluent UI v9。视觉读取是 Windows 原生生产力工具，不是营销页面。设计参数为：

- `DESIGN_VARIANCE: 3`
- `MOTION_INTENSITY: 2`
- `VISUAL_DENSITY: 8`

采用中性灰背景与单一青绿色强调色。圆角系统固定为：输入和按钮 6px、面板 8px、圆形头像除外。动画仅用于状态切换和加载反馈，并遵守减少动态效果设置。

桌面主框架分为三栏：

1. 左侧 248px：工作区、Bot 名册、群组、搜索、Routine 和设置入口。
2. 中央自适应：对话、任务时间线、附件和消息输入。
3. 右侧 360px 可折叠检查器：当前任务、Agent Computer、审批、产物、成本和日志。

一级页面包括：工作台、Bot、任务、审批、Routines、Skills、模型、工具、Workers、审计和设置。工作台显示真实状态，不使用装饰性假数据。空状态提供直接操作；加载状态使用与最终布局一致的骨架；错误状态显示请求 ID、重试和诊断入口。

## 9. API 与实时协议

REST 用于资源创建和查询，SSE 用于服务器到桌面端的任务事件。首版端点：

- `GET/POST /api/v1/bots`
- `GET/PATCH/DELETE /api/v1/bots/{id}`
- `POST /api/v1/conversations`
- `POST /api/v1/conversations/{id}/messages`
- `GET /api/v1/tasks/{id}`
- `POST /api/v1/tasks/{id}/cancel`
- `GET /api/v1/tasks/{id}/events`
- `GET/POST /api/v1/approvals`
- `POST /api/v1/approvals/{id}/decision`
- `GET/POST /api/v1/providers`
- `POST /api/v1/providers/{id}/test`
- `GET /api/v1/models`
- `GET/POST /api/v1/skills`
- `GET/POST /api/v1/routines`
- `POST /api/v1/routines/{id}/test-run`
- `GET /api/v1/workers`
- `GET /api/v1/health`

错误采用 Problem Details JSON。所有写请求支持 `Idempotency-Key`。SSE 事件包含单调递增 ID，客户端用 `Last-Event-ID` 重连。桌面网络层使用原生 fetch、AbortController 和 TanStack Query，不把供应商密钥放入渲染进程。

## 10. 测试与验收

- 单元测试：状态机、能力校验、策略优先级、预算、幂等和调度。
- API 测试：Bot CRUD、任务创建、审批恢复、SSE 补流和错误格式。
- Worker 测试：模型工具循环、取消、超时、检查点和重试。
- 适配器契约测试：使用本地假服务器验证各供应商请求差异，不消耗真实额度。
- UI 测试：主要页面、空态、错误态、审批操作和模型配置。
- 端到端测试：Docker Compose 启动后创建 Bot，使用确定性测试模型执行工具任务，验证事件、产物和审批。
- Windows 验收：桌面开发启动、生产构建、安装包生成，以及连接 Docker 后端。

完成标准不是容器健康，而是一条真实任务从桌面创建、经过 Worker、产生可核验产物并完整出现在审计时间线中。真实付费模型验证需由用户提供密钥并明确同意产生费用后执行。

