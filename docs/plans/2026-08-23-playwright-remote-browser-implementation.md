# Playwright Remote Browser Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a containerized, interactive remote Playwright browser controlled from the Windows desktop through audited Super Bot APIs.

**Architecture:** Run an official Playwright Server in an internal container, connect from a Python Browser Gateway with `BrowserType.connect()`, and proxy every session/action through FastAPI. Persist control-plane session metadata and redacted action audits in PostgreSQL while keeping ephemeral Playwright handles inside the gateway.

**Tech Stack:** Python 3.12, FastAPI, Playwright Python 1.61, SQLAlchemy/Alembic, httpx, PostgreSQL, Docker Compose, React 19, TanStack Query, Fluent UI, Vitest.

---

### Task 1: Define and test the browser execution contract

**Files:**
- Create: `tests/worker/test_browser_gateway.py`
- Modify: `tests/worker/test_sandbox.py`
- Modify: `apps/worker/superbot_worker/browser.py`
- Create: `apps/worker/superbot_worker/browser_gateway.py`

1. Write failing tests for session creation, public navigation, private-network blocking, screenshots, coordinate clicks, typing, key presses, scrolling and close.
2. Run `uv run pytest tests/worker/test_browser_gateway.py tests/worker/test_sandbox.py -v` and confirm failures describe missing behavior.
3. Implement strict action models, injected Playwright adapter, session registry, request routing and snapshot generation.
4. Re-run the targeted tests until green, then refactor without changing behavior.

### Task 2: Persist sessions and audited actions behind the API

**Files:**
- Create: `tests/api/test_browser.py`
- Modify: `apps/api/superbot_api/persistence/tables.py`
- Modify: `apps/api/superbot_api/persistence/repositories.py`
- Create: `apps/api/superbot_api/api/browser.py`
- Create: `apps/api/superbot_api/browser_gateway.py`
- Modify: `apps/api/superbot_api/main.py`
- Create: `apps/api/alembic/versions/0002_browser_sessions.py`

1. Write failing API tests for create/list/get/action/close, ownership, unavailable gateway and redacted audit data.
2. Run `uv run pytest tests/api/test_browser.py -v` and verify red.
3. Implement SQLAlchemy records, Alembic migration, gateway client, endpoints and error mapping.
4. Run the API tests and relevant repository tests until green.

### Task 3: Add the desktop interactive browser console

**Files:**
- Create: `apps/desktop/src/features/browser/BrowserView.test.tsx`
- Create: `apps/desktop/src/features/browser/BrowserView.tsx`
- Modify: `apps/desktop/src/api/queries.ts`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src/main.tsx`
- Modify: `apps/desktop/src/components/Sidebar.tsx`
- Modify: `apps/desktop/src/styles.css`

1. Write failing component tests for creating a session, navigating, coordinate clicking, typing, key presses and closing.
2. Run `pnpm --filter @superbot/desktop test --run src/features/browser/BrowserView.test.tsx` and verify red.
3. Implement typed React Query hooks and the presentational browser console with accessible controls and accurate screenshot scaling.
4. Re-run targeted tests, then all desktop tests and type checking.

### Task 4: Containerize the remote Playwright path

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `Dockerfile.worker`
- Modify: `docker-compose.yml`
- Modify: `.env.example`
- Modify: `tests/deployment/test_compose_contract.py`

1. Add failing Compose contract tests requiring an internal Playwright Server, version match, Browser Gateway health check and no published browser ports.
2. Run the deployment tests and verify red.
3. Add the Playwright dependency, internal server service, gateway command/environment/dependencies and security/resource limits.
4. Validate `docker compose --profile browser config --quiet` and run the deployment tests.

### Task 5: Documentation and production-equivalent verification

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/security.md`
- Modify: `docs/windows.md`

1. Document configuration, lifecycle, security limits and external Playwright endpoint replacement.
2. Run `uv run ruff check .`, `uv run pytest -q`, `pnpm lint`, `pnpm test --run`, and `pnpm build`.
3. Start the browser Compose profile and perform a real public-page navigation, input/click interaction and PNG validation through the API.
4. Inspect service health/logs, stop only the verification stack, and report any unverified boundary explicitly.
