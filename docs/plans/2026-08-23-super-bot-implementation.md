# Super Bot Complete Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Windows-first, container-deployable persistent AI teammate platform with explicit multi-model routing, durable tasks, approvals, routines, skills, audit events, and an Electron desktop control plane.

**Architecture:** Use a pnpm monorepo for the Electron/React desktop and shared TypeScript contracts, plus a Python FastAPI service for durable orchestration and a Python worker for agent execution. PostgreSQL is the source of truth and lease queue, Valkey provides Redis-compatible coordination, and S3-compatible storage holds artifacts. Development supports an in-memory profile so domain and UI tests stay fast while Docker Compose provides the production-equivalent path.

**Tech Stack:** Electron, React 19, TypeScript, Vite, Fluent UI v9, TanStack Query, Vitest, Python 3.12+, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic, pytest, PostgreSQL, Valkey, SeaweedFS, Docker Compose.

---

### Task 1: Monorepo and quality gates

**Files:**
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `pyproject.toml`
- Create: `apps/api/superbot_api/__init__.py`
- Create: `apps/worker/superbot_worker/__init__.py`
- Create: `packages/contracts/package.json`
- Create: `packages/contracts/src/index.ts`
- Create: `tests/test_project_layout.py`

**Step 1: Write the failing test**

```python
def test_expected_service_packages_are_importable():
    import superbot_api
    import superbot_worker
    assert superbot_api.__version__ == superbot_worker.__version__
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_project_layout.py -v`

Expected: FAIL because the workspace packages and metadata do not exist.

**Step 3: Write minimal implementation**

Create the workspace manifests, Python package discovery, shared lint/test configuration, and matching package versions.

**Step 4: Run test to verify it passes**

Run: `uv sync --all-groups && uv run pytest tests/test_project_layout.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add package.json pnpm-workspace.yaml pyproject.toml apps packages tests
git commit -m "build: scaffold super bot workspace"
```

### Task 2: Domain contracts and task state machine

**Files:**
- Create: `apps/api/superbot_api/domain/enums.py`
- Create: `apps/api/superbot_api/domain/models.py`
- Create: `apps/api/superbot_api/domain/task_state.py`
- Create: `tests/domain/test_task_state.py`
- Modify: `packages/contracts/src/index.ts`

**Step 1: Write failing transition tests**

```python
def test_approval_pause_can_resume_to_running():
    assert transition(TaskStatus.WAITING_APPROVAL, TaskEvent.APPROVED) is TaskStatus.RUNNING

def test_terminal_task_rejects_new_work():
    with pytest.raises(InvalidTransition):
        transition(TaskStatus.SUCCEEDED, TaskEvent.START)
```

Cover queued, running, waiting approval, succeeded, failed, cancelled, retryable failure, and lease expiry.

**Step 2: Run RED**

Run: `uv run pytest tests/domain/test_task_state.py -v`

Expected: FAIL because domain modules are missing.

**Step 3: Implement the state machine and contracts**

Use enums and an explicit transition table. Add Bot, Task, TaskEvent, Approval, Artifact, Provider, Model, Skill, Routine, UsageRecord, and Worker schemas. Mirror API-facing shapes in TypeScript.

**Step 4: Run GREEN**

Run: `uv run pytest tests/domain/test_task_state.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/superbot_api/domain packages/contracts tests/domain
git commit -m "feat: define durable agent domain"
```

### Task 3: Configuration, database, and repositories

**Files:**
- Create: `apps/api/superbot_api/config.py`
- Create: `apps/api/superbot_api/db.py`
- Create: `apps/api/superbot_api/persistence/tables.py`
- Create: `apps/api/superbot_api/persistence/repositories.py`
- Create: `apps/api/alembic.ini`
- Create: `apps/api/alembic/env.py`
- Create: `apps/api/alembic/versions/0001_initial.py`
- Create: `tests/persistence/test_repositories.py`

**Step 1: Write failing repository tests**

Test Bot creation, event ordering, idempotent task creation, approval decisions, and routine run uniqueness against SQLite. Tests must exercise real SQLAlchemy repositories.

**Step 2: Run RED**

Run: `uv run pytest tests/persistence/test_repositories.py -v`

Expected: FAIL because repositories do not exist.

**Step 3: Implement persistence**

Use UUIDv7-compatible IDs, UTC timestamps, JSON columns for extensible settings, unique idempotency keys, append-only task events, and optimistic version fields.

**Step 4: Run GREEN**

Run: `uv run pytest tests/persistence/test_repositories.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api tests/persistence
git commit -m "feat: add durable repositories"
```

### Task 4: Explicit multi-model gateway

**Files:**
- Create: `apps/api/superbot_api/models/capabilities.py`
- Create: `apps/api/superbot_api/models/catalog.py`
- Create: `apps/api/superbot_api/models/gateway.py`
- Create: `apps/api/superbot_api/models/openai_compatible.py`
- Create: `apps/api/superbot_api/models/providers.py`
- Create: `tests/models/test_catalog.py`
- Create: `tests/models/test_gateway.py`

**Step 1: Write failing capability and no-silent-fallback tests**

```python
async def test_gateway_never_falls_back_without_explicit_chain(fake_server):
    gateway = ModelGateway(registry_with_primary_only(fake_server))
    with pytest.raises(ModelUnavailable):
        await gateway.complete(model_id="qwen3.7-plus", request=request())
```

Verify provider-specific request bodies for Qwen thinking mode, DeepSeek, Kimi, GLM, MiniMax, SiliconFlow, Ollama, and custom OpenAI-compatible endpoints.

**Step 2: Run RED**

Run: `uv run pytest tests/models -v`

Expected: FAIL because the gateway is missing.

**Step 3: Implement the model registry and gateway**

Use `httpx.AsyncClient`, typed errors, timeouts, response status validation, SSE parsing, token usage extraction, explicit fallback chains, and redacted diagnostics.

**Step 4: Run GREEN**

Run: `uv run pytest tests/models -v`

Expected: PASS with no network access.

**Step 5: Commit**

```bash
git add apps/api/superbot_api/models tests/models
git commit -m "feat: add explicit domestic model gateway"
```

### Task 5: Policy, budget, and approval engine

**Files:**
- Create: `apps/api/superbot_api/policy/risk.py`
- Create: `apps/api/superbot_api/policy/engine.py`
- Create: `apps/api/superbot_api/policy/budget.py`
- Create: `tests/policy/test_policy_engine.py`
- Create: `tests/policy/test_budget.py`

**Step 1: Write failing policy tests**

Test read defaults, sensitive approvals, critical actions, deny-overrides-allow, narrow scope matching, token budgets, monetary budgets, and exhausted budgets.

**Step 2: Run RED**

Run: `uv run pytest tests/policy -v`

Expected: FAIL.

**Step 3: Implement deterministic policy evaluation**

Return `allow`, `require_approval`, or `deny` with an ordered explanation. Never use a model as the only policy enforcement mechanism.

**Step 4: Run GREEN**

Run: `uv run pytest tests/policy -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/superbot_api/policy tests/policy
git commit -m "feat: enforce approvals and hard budgets"
```

### Task 6: Tool registry and agent loop

**Files:**
- Create: `apps/worker/superbot_worker/tools/base.py`
- Create: `apps/worker/superbot_worker/tools/files.py`
- Create: `apps/worker/superbot_worker/tools/http.py`
- Create: `apps/worker/superbot_worker/tools/mcp.py`
- Create: `apps/worker/superbot_worker/agent/runtime.py`
- Create: `apps/worker/superbot_worker/agent/context.py`
- Create: `tests/worker/test_tool_registry.py`
- Create: `tests/worker/test_agent_runtime.py`

**Step 1: Write failing agent-loop tests**

Exercise a deterministic fake model that emits one tool call then a final answer. Verify policy denial, approval pause, cancellation, maximum steps, artifact creation, and explicit provider failure.

**Step 2: Run RED**

Run: `uv run pytest tests/worker/test_tool_registry.py tests/worker/test_agent_runtime.py -v`

Expected: FAIL.

**Step 3: Implement minimal runtime**

Define JSON Schema tools, normalized ToolResult, cancellation checks between steps, event callbacks, context compaction boundaries, and structured exceptions.

**Step 4: Run GREEN**

Run: `uv run pytest tests/worker/test_tool_registry.py tests/worker/test_agent_runtime.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/worker tests/worker
git commit -m "feat: execute auditable agent tool loops"
```

### Task 7: FastAPI product API and SSE

**Files:**
- Create: `apps/api/superbot_api/main.py`
- Create: `apps/api/superbot_api/api/dependencies.py`
- Create: `apps/api/superbot_api/api/errors.py`
- Create: `apps/api/superbot_api/api/bots.py`
- Create: `apps/api/superbot_api/api/tasks.py`
- Create: `apps/api/superbot_api/api/approvals.py`
- Create: `apps/api/superbot_api/api/models.py`
- Create: `apps/api/superbot_api/api/skills.py`
- Create: `apps/api/superbot_api/api/routines.py`
- Create: `apps/api/superbot_api/api/workers.py`
- Create: `tests/api/test_bots.py`
- Create: `tests/api/test_tasks.py`
- Create: `tests/api/test_approvals.py`

**Step 1: Write failing API tests**

Verify health, Bot CRUD, message-to-task creation, idempotency, cancellation, approval decision, model listing, Problem Details errors, SSE event IDs, and `Last-Event-ID` replay.

**Step 2: Run RED**

Run: `uv run pytest tests/api -v`

Expected: FAIL.

**Step 3: Implement API routes**

Use async routes and repositories, explicit response models, stable `/api/v1` paths, request IDs, no secret fields in responses, and heartbeat comments for SSE.

**Step 4: Run GREEN**

Run: `uv run pytest tests/api -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/api/superbot_api/api apps/api/superbot_api/main.py tests/api
git commit -m "feat: expose super bot control API"
```

### Task 8: Queue worker, routines, skills, and browser sandbox

**Files:**
- Create: `apps/worker/superbot_worker/queue.py`
- Create: `apps/worker/superbot_worker/service.py`
- Create: `apps/worker/superbot_worker/scheduler.py`
- Create: `apps/worker/superbot_worker/skills.py`
- Create: `apps/worker/superbot_worker/browser.py`
- Create: `apps/worker/superbot_worker/sandbox.py`
- Create: `tests/worker/test_scheduler.py`
- Create: `tests/worker/test_skills.py`
- Create: `tests/worker/test_sandbox.py`

**Step 1: Write failing durable execution tests**

Test routine timezone calculation, deterministic idempotency keys, stale lease recovery, Skill parsing and version hashes, browser target restrictions, and safe Docker arguments.

**Step 2: Run RED**

Run: `uv run pytest tests/worker -v`

Expected: FAIL for new behavior.

**Step 3: Implement durable worker services**

Use PostgreSQL leases in deployment, an in-memory queue in unit tests, durable approval checkpoints, Cron schedules, non-root container policy, and browser policy/screenshot hooks.

**Step 4: Run GREEN**

Run: `uv run pytest tests/worker -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/worker tests/worker
git commit -m "feat: add durable routines and sandbox execution"
```

### Task 9: Electron shell and Fluent UI desktop

**Files:**
- Create: `apps/desktop/package.json`
- Create: `apps/desktop/electron/main.ts`
- Create: `apps/desktop/electron/preload.ts`
- Create: `apps/desktop/src/main.tsx`
- Create: `apps/desktop/src/App.tsx`
- Create: `apps/desktop/src/theme.ts`
- Create: `apps/desktop/src/styles.css`
- Create: `apps/desktop/src/components/AppShell.tsx`
- Create: `apps/desktop/src/components/Sidebar.tsx`
- Create: `apps/desktop/src/components/Inspector.tsx`
- Create: `apps/desktop/src/App.test.tsx`

**Step 1: Write failing shell tests**

Test landmarks, keyboard navigation, theme behavior, three-column layout, collapsed inspector, loading state, empty state, and API error state.

**Step 2: Run RED**

Run: `pnpm --filter @superbot/desktop test --run`

Expected: FAIL because the desktop package is missing.

**Step 3: Implement desktop shell**

Install and use Fluent UI v9 and Phosphor icons only. Keep Electron context isolation enabled, node integration disabled, and expose a minimal typed preload API.

**Step 4: Run GREEN**

Run: `pnpm --filter @superbot/desktop test --run`

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/desktop package.json pnpm-lock.yaml
git commit -m "feat: build Windows desktop control shell"
```

### Task 10: Desktop product flows and reliable networking

**Files:**
- Create: `apps/desktop/src/api/client.ts`
- Create: `apps/desktop/src/api/queries.ts`
- Create: `apps/desktop/src/features/bots/BotList.tsx`
- Create: `apps/desktop/src/features/chat/Conversation.tsx`
- Create: `apps/desktop/src/features/chat/Composer.tsx`
- Create: `apps/desktop/src/features/tasks/TaskTimeline.tsx`
- Create: `apps/desktop/src/features/approvals/ApprovalCenter.tsx`
- Create: `apps/desktop/src/features/models/ModelCenter.tsx`
- Create: `apps/desktop/src/features/routines/RoutineCenter.tsx`
- Create: `apps/desktop/src/features/audit/AuditView.tsx`
- Create: `apps/desktop/src/features/workers/WorkerView.tsx`
- Create: `apps/desktop/src/api/client.test.ts`
- Create: `apps/desktop/src/features/chat/Conversation.test.tsx`

**Step 1: Write failing client and flow tests**

Test typed HTTP errors, timeout cancellation, safe GET retries only, SSE reconnection, task creation, approval actions, model configuration without rendering secrets, and empty/error states.

**Step 2: Run RED**

Run: `pnpm --filter @superbot/desktop test --run`

Expected: FAIL.

**Step 3: Implement product flows**

Use native fetch, AbortController, TanStack Query caching, stable query keys, mutation invalidation, and an SSE client with cursor replay. Do not retry non-idempotent writes without an idempotency key.

**Step 4: Run GREEN**

Run: `pnpm --filter @superbot/desktop test --run`

Expected: PASS.

**Step 5: Commit**

```bash
git add apps/desktop
git commit -m "feat: connect desktop agent workflows"
```

### Task 11: Containerized deployment and Windows scripts

**Files:**
- Create: `Dockerfile.api`
- Create: `Dockerfile.worker`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `deploy/postgres/init.sql`
- Create: `scripts/dev.ps1`
- Create: `scripts/build-windows.ps1`
- Create: `scripts/verify-compose.ps1`
- Create: `tests/deployment/test_compose_contract.py`

**Step 1: Write failing deployment contract tests**

Parse Compose configuration and verify non-root containers, health checks, named volumes, no baked secrets, required dependencies, resource limits, and Windows-safe commands.

**Step 2: Run RED**

Run: `uv run pytest tests/deployment/test_compose_contract.py -v`

Expected: FAIL.

**Step 3: Implement deployment files**

Add API, worker, scheduler, PostgreSQL, Valkey, and SeaweedFS. Keep the browser execution role optional through a Compose profile. Preserve state in named volumes.

**Step 4: Run GREEN and render Compose**

Run: `uv run pytest tests/deployment/test_compose_contract.py -v`

Run: `docker compose config --quiet`

Expected: both exit 0.

**Step 5: Commit**

```bash
git add Dockerfile.api Dockerfile.worker docker-compose.yml .env.example deploy scripts tests/deployment
git commit -m "build: containerize super bot services"
```

### Task 12: Documentation, full verification, and production build

**Files:**
- Create: `README.md`
- Create: `docs/architecture.md`
- Create: `docs/security.md`
- Create: `docs/model-providers.md`
- Create: `docs/windows.md`
- Create: `tests/e2e/test_task_lifecycle.py`
- Modify: `package.json`
- Modify: `pyproject.toml`

**Step 1: Write failing end-to-end lifecycle test**

Create a Bot, submit a deterministic task, observe a tool call, require approval, approve it, receive a result artifact, and verify the audit sequence and cost record.

**Step 2: Run RED**

Run: `uv run pytest tests/e2e/test_task_lifecycle.py -v`

Expected: FAIL until all application wiring is complete.

**Step 3: Wire entry points and write operational documentation**

Document local development, Docker deployment, Windows packaging, provider setup, security boundaries, backup, recovery, and paid-model verification rules.

**Step 4: Run the complete verification matrix**

```bash
uv run ruff check .
uv run pytest -q
pnpm lint
pnpm test --run
pnpm build
docker compose config --quiet
docker compose build api worker scheduler
docker compose up -d postgres valkey seaweedfs api worker scheduler
docker compose ps
uv run pytest tests/e2e/test_task_lifecycle.py -v
pnpm --filter @superbot/desktop package:win
```

Expected: all commands exit 0, all required containers are healthy, the deterministic task completes with a valid artifact, and the Windows installer is generated.

**Step 5: Review and commit**

Inspect `git diff --check`, secret scans, dependency licenses, generated installer path, container health, and exact test counts before the final commit.

```bash
git add .
git commit -m "feat: deliver super bot desktop platform"
```
