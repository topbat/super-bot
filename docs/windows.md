# Windows 与容器部署

## 1. 准备

安装 Windows 10/11 x64、Docker Desktop（Linux containers）、PowerShell 7、Node.js 22+、pnpm 10.32+ 和 uv。为 Docker Desktop 分配至少 6 GB 内存；Browser profile 需要更多资源。

```powershell
Copy-Item .env.example .env
```

编辑 `.env`，设置三个必填值：`POSTGRES_PASSWORD`、`S3_ACCESS_KEY`、`S3_SECRET_KEY`。再设置至少一个模型 Key，或准备 Ollama。不要复用生产数据库密码。

## 2. 启动

```powershell
pnpm install --frozen-lockfile
uv sync --frozen
.\scripts\dev.ps1 -NoDesktop
.\scripts\verify-compose.ps1
pnpm --filter '@superbot/desktop' dev
```

API 只监听 `127.0.0.1:8420`。数据保存在 `postgres-data`、`valkey-data`、`seaweedfs-data`、`bot-workspaces` 命名卷。常规更新不要使用 `down -v`。

### 启用远程浏览器

```powershell
docker compose --profile browser build playwright-server browser-worker
docker compose --profile browser up -d playwright-server browser-worker
docker compose --profile browser ps
```

首次需要下载约 790 MB 的官方 Chromium 镜像。Playwright Server 和 Python 客户端固定为同一版本，3000/8430 仅在 Compose 网络内暴露。若使用 Clash/TUN Fake-IP DNS，并确认公开域名被可信代理映射到 `198.18.0.0/15`，可在 `.env` 设置：

```dotenv
SUPERBOT_BROWSER_TRUSTED_DNS_PROXY_CIDRS=198.18.0.0/15
```

没有这种 DNS 代理时保持为空。不要为解决访问问题直接允许私网或发布 Playwright WebSocket 端口。

## 3. 构建安装器

```powershell
.\scripts\build-windows.ps1
```

输出为 `apps/desktop/release/Super-Bot-Setup-<version>-x64.exe`。安装器支持选择安装目录，创建开始菜单与桌面快捷方式，卸载默认保留应用数据。正式对外发布前配置 Authenticode 证书和品牌 `.ico`。

## 4. 更新

```powershell
docker compose stop api worker scheduler
docker compose build --no-cache api worker scheduler
docker compose up -d --no-deps --force-recreate api worker scheduler
.\scripts\verify-compose.ps1
```

这组命令不会重建 PostgreSQL、Valkey、SeaweedFS，也不会删除卷。涉及数据库 migration 时先备份，再让 API 启动命令执行 Alembic。

## 5. 备份与恢复

备份至少包括：PostgreSQL 逻辑备份、SeaweedFS 数据卷和 Bot workspace。Valkey 不是事实源，但保留它有助于减少恢复后的重传。恢复时先恢复数据库和对象存储，再启动 API，最后启动 Worker/Scheduler，并抽查 Artifact 的 SHA-256。

## 6. 故障排查

- Docker 管道不存在：启动 Docker Desktop，确认 `docker info` 成功。
- 8420 绑定失败：先检查监听者，再检查 Windows 排除端口范围。
- Worker 离线：查看 `/api/v1/workers` 的 `last_seen_at`，再查容器日志与数据库连接。
- 模型任务失败：确认选择的 provider Key 和模型权限；系统不会静默 fallback。
- SeaweedFS 首次拉取慢：可先单独 `docker pull chrislusf/seaweedfs:4.38`，完成后再 `docker compose up`。
- 浏览器 profile 不健康：分别检查 `playwright-server` 与 `browser-worker` 日志；确认两端 Playwright 版本一致，并检查代理 DNS 是否返回 Fake-IP。
- Installer 被 SmartScreen 提示：开发构建未签名；正式发布需可信代码签名证书。
