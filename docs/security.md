# 安全模型

## 默认边界

- Electron：`contextIsolation=true`、`nodeIntegration=false`、`sandbox=true`，preload 只暴露平台、版本和 API 地址。
- 应用容器：固定非 root UID/GID、只读根文件系统、移除全部 Linux capabilities、`no-new-privileges`、资源限制和受限 tmpfs。
- 文件工具：只接受相对路径，解析后的路径必须位于 Bot 工作区。
- HTTP/浏览器：只允许 HTTP(S)，阻断 localhost、私网、保留地址、链路本地与元数据 IP；浏览器策略在 DNS 解析后再次检查，降低 DNS rebinding 风险。
- 外部写操作：根据风险等级进入审批；deny 优先于 allow。批准与拒绝均写审计事件。
- 密钥：数据库只保存 `env:` 等外部引用，API 不返回明文。`.env` 被 Git 忽略，示例文件不包含有效凭据。

## 重要事实

Bot 是职责和上下文边界，不应被当作强安全租户。当前默认每个 Bot 有独立工作区目录，但同一个 Worker 与部署管理员仍能访问宿主范围内的数据。需要强租户隔离时，应使用独立部署、独立存储凭据和网络边界。

模型输出是不可信输入。模型生成的工具名和参数必须经过：schema 校验、ToolRegistry 查找、策略判定、路径/网络检查、预算检查和审计。任何“系统提示词要求绕过审批”都不能改变确定性策略结果。

## 部署建议

1. 只在 `127.0.0.1` 发布 API；远程使用时放到具备 TLS、身份认证和速率限制的反向代理后。
2. 为 PostgreSQL 与 S3 使用随机长密码；不要把 `.env` 提交到版本库。
3. 只配置实际需要的供应商 Key，并给供应商账户设置额度。
4. 默认不开 Browser profile；启用浏览器前设置域名 allowlist 和独立低权限账户。
5. 不在聊天中粘贴密码、Cookie、一次性验证码或私钥。
6. 定期备份 PostgreSQL 和 SeaweedFS 数据卷，并进行恢复演练。
7. 对发布、发送、购买、删除和生产变更保留人工审批。

## 已知边界

- 当前 API 面向本机单用户部署，尚未内置 OIDC/多租户 RBAC。
- Browser Worker 尚未接入完整 Playwright 远程动作协议。
- token 用量已记录；只有配置了可信单价后才能计算真实货币成本，当前不会捏造费用。
- Windows 安装器当前未使用商业代码签名证书，SmartScreen 可能提示未知发布者。
