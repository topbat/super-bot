# Playwright 远程交互浏览器设计

## 目标

把现有 Browser Worker 的策略与心跳骨架升级为真正可用的远程浏览器：用户在 Windows 桌面端创建会话、打开网页、查看远程截图，并可在画面上点击、输入、按键、滚动和前进后退。所有动作经过 Super Bot API，写入持久化审计记录；浏览器进程与控制面隔离，可替换为外部 Playwright Server。

## 推荐架构

采用四层分离：Electron 只调用 FastAPI；FastAPI 持久化会话与动作并代理内部 Browser Gateway；Browser Gateway 持有 Playwright `Browser`、`BrowserContext` 和 `Page` 的内存句柄；独立官方 Playwright 容器运行 `run-server` 并通过 WebSocket 接受 Gateway 的 `BrowserType.connect()`。客户端和服务端锁定相同 Playwright 版本，避免协议漂移。外部部署可只替换 `SUPERBOT_PLAYWRIGHT_WS_ENDPOINT`，无需改桌面端或 API。

浏览器会话的数据库记录是控制面事实来源，包含所属 Bot、状态、当前 URL、标题、视口、允许域和时间戳。Playwright 页面句柄不伪装为可跨进程持久化；Browser Gateway 重启后，存量活动会话会在下一次调用时明确标记失败，用户可重新创建。动作审计不保存输入明文，只记录长度和已脱敏标记。

## 数据链路

1. 桌面端 `POST /browser/sessions`，API 验证 Bot 并要求 Browser Gateway 创建同 ID 会话。
2. Gateway 连接远程 Playwright Server，创建禁用 Service Worker、下载和多余权限的隔离 Context。
3. 用户点击远程截图时，桌面端把缩放后的坐标换算为视口坐标并提交 `click` 动作；输入、按键、滚动、导航同样通过动作 API。
4. Gateway 每次动作后返回 URL、标题、视口、PNG 截图和可交互元素摘要；API 更新会话并写入脱敏动作记录。
5. 桌面端用 React Query 失效/刷新会话状态，不直接接触 Playwright WebSocket 或内部 Gateway 地址。

## 安全边界

- 只允许 HTTP(S)，阻断 localhost、`.local`、私有/链路本地/保留/元数据 IP，并在 DNS 解析后再次检查，降低 DNS rebinding 风险。
- 页面所有 HTTP(S) 请求都经过 Context 路由策略；重定向后的主页面 URL再次校验。
- 默认关闭下载、Service Worker 和权限；不暴露任意 JavaScript `evaluate` 接口。
- 动作集合使用严格枚举和 Pydantic `extra=forbid`；坐标、滚动量、按键和输入长度设硬限制。
- 浏览器容器不发布宿主端口，Gateway 也只在 Compose 内网可见；API 是唯一桌面入口。
- 审计记录脱敏输入内容；截图属于敏感数据，当前仅随请求返回，不写日志。后续需要长期保留时应接入现有 S3 ArtifactStore 和保留策略。

## 错误处理与可观测性

Gateway 区分会话不存在、目标被策略拒绝、动作无效和远程 Playwright 不可用。API 分别映射为 404、403、422 和 503/502，并保留请求 ID。Browser Worker 心跳能力扩展为 `playwright-remote`、`interactive-screenshot`、`browser-policy`。健康检查同时验证 Gateway 进程和 Playwright WebSocket 连接能力。

## 验收标准

- 单元测试证明 URL/DNS 策略、动作校验、截图状态和输入审计脱敏。
- API 测试覆盖创建、列举、动作、关闭、跨 Bot 访问和 Gateway 故障。
- 前端测试覆盖创建会话、URL 导航、截图坐标点击、输入与关闭。
- Compose `browser` profile 能启动 Playwright Server 与 Browser Gateway，并对公开测试页完成真实导航、点击、输入和截图。
- 完整 Python、TypeScript、构建及 Compose 配置门禁通过。
