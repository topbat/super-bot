from __future__ import annotations

import argparse
import asyncio
import logging
import socket
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

from anyio import Path as AsyncPath
from redis.asyncio import Redis
from sqlalchemy import select
from superbot_api.config import get_settings
from superbot_api.db import create_database
from superbot_api.models.catalog import built_in_catalog
from superbot_api.models.gateway import EnvironmentSecretResolver, ModelGateway
from superbot_api.models.providers import default_provider_configs
from superbot_api.persistence.repositories import TaskRepository
from superbot_api.persistence.tables import MessageTable, TaskTable, WorkerTable

from superbot_worker.artifacts import S3ArtifactStore
from superbot_worker.browser import BrowserPolicy
from superbot_worker.execution import ExecutionCoordinator
from superbot_worker.queue import InMemoryDurableQueue, QueueItem
from superbot_worker.scheduler import dispatch_due_routines

LOGGER = logging.getLogger(__name__)


class WorkerService:
    def __init__(
        self,
        *,
        worker_id: str,
        queue: InMemoryDurableQueue,
        handler: Callable[[QueueItem], Awaitable[None]],
        lease_seconds: int = 60,
    ) -> None:
        self.worker_id = worker_id
        self.queue = queue
        self.handler = handler
        self.lease_seconds = lease_seconds

    async def run_once(self) -> bool:
        self.queue.recover_stale(now=datetime.now(UTC))
        item = self.queue.lease(
            self.worker_id, now=datetime.now(UTC), lease_seconds=self.lease_seconds
        )
        if item is None:
            return False
        await self.handler(item)
        self.queue.acknowledge(item.id, self.worker_id)
        return True

    async def serve(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            if not await self.run_once():
                try:
                    await asyncio.wait_for(stop.wait(), timeout=0.5)
                except TimeoutError:
                    pass


async def run_role(role: str) -> None:
    if role not in {"worker", "scheduler", "browser"}:
        raise ValueError(f"unknown worker role: {role}")
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.ping()
        if role == "worker":
            from superbot_worker.queue import RedisStreamQueue

            await RedisStreamQueue(redis).ensure_group("superbot-workers")
        ready_path = AsyncPath(f"/tmp/superbot-{role}.ready")
        await ready_path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
        if role == "worker":
            await run_database_worker(ready_path)
        elif role == "scheduler":
            await run_scheduler(ready_path)
        else:
            await run_browser_heartbeat(ready_path, redis)
    finally:
        await redis.aclose()


async def run_database_worker(ready_path: AsyncPath) -> None:
    settings = get_settings()
    database = create_database(settings.database_url)
    model = ModelGateway(
        built_in_catalog(),
        default_provider_configs(),
        EnvironmentSecretResolver(),
    )
    secrets = EnvironmentSecretResolver()
    access_key = await secrets.resolve(settings.s3_access_key_ref)
    secret_key = await secrets.resolve(settings.s3_secret_key_ref)
    assert access_key is not None and secret_key is not None
    artifact_store = S3ArtifactStore(
        endpoint_url=settings.s3_endpoint_url,
        bucket=settings.s3_bucket,
        access_key=access_key,
        secret_key=secret_key,
    )
    await artifact_store.ensure_bucket()
    coordinator = ExecutionCoordinator(
        database=database,
        model=model,
        workspace_root=Path("/workspaces"),
        artifact_store=artifact_store,
    )
    worker_id = f"{socket.gethostname()}:{id(asyncio.current_task())}"
    try:
        while True:
            await record_worker_heartbeat(
                database,
                worker_id=worker_id,
                role="worker",
                capabilities=["files", "http", "mcp"],
            )
            user_text = ""
            async with database.sessions() as session:
                claimed = await TaskRepository(session).claim_next(worker_id)
                if claimed is not None:
                    task_row = await session.get(TaskTable, claimed.id)
                    if task_row is not None and task_row.checkpoint is None:
                        user_text = (
                            await session.scalar(
                                select(MessageTable.content).where(
                                    MessageTable.id == task_row.message_id
                                )
                            )
                        ) or ""
            if claimed is None:
                await asyncio.sleep(0.5)
            else:
                try:
                    await coordinator.execute(claimed.id, user_text=user_text)
                except Exception:
                    # The coordinator records a sanitized failure event before surfacing.
                    LOGGER.exception("task execution failed", extra={"task_id": str(claimed.id)})
            await ready_path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
    finally:
        await database.engine.dispose()


async def run_scheduler(ready_path: AsyncPath) -> None:
    database = create_database(get_settings().database_url)
    worker_id = f"{socket.gethostname()}:scheduler"
    try:
        while True:
            await record_worker_heartbeat(
                database,
                worker_id=worker_id,
                role="scheduler",
                capabilities=["routines"],
            )
            await dispatch_due_routines(database, now=datetime.now(UTC))
            await ready_path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
            await asyncio.sleep(1)
    finally:
        await database.engine.dispose()


async def run_browser_heartbeat(ready_path: AsyncPath, redis: Redis) -> None:
    import uvicorn

    from superbot_worker.browser_gateway import (
        BrowserSessionRegistry,
        PlaywrightConnector,
        create_gateway_app,
    )

    settings = get_settings()
    database = create_database(settings.database_url)
    worker_id = f"{socket.gethostname()}:browser"
    registry = BrowserSessionRegistry(
        connector=PlaywrightConnector(settings.playwright_ws_endpoint),
        policy_factory=lambda domains: BrowserPolicy(
            allowed_domains=domains,
            trusted_dns_proxy_cidrs={
                cidr.strip()
                for cidr in settings.browser_trusted_dns_proxy_cidrs.split(",")
                if cidr.strip()
            },
        ),
    )
    server = uvicorn.Server(
        uvicorn.Config(
            create_gateway_app(registry),
            host=settings.browser_gateway_host,
            port=settings.browser_gateway_port,
            log_level="info",
            access_log=False,
        )
    )

    async def heartbeat() -> None:
        while True:
            await redis.ping()
            await record_worker_heartbeat(
                database,
                worker_id=worker_id,
                role="browser",
                capabilities=[
                    "browser-policy",
                    "interactive-screenshot",
                    "playwright-remote",
                ],
            )
            await ready_path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
            await asyncio.sleep(10)

    heartbeat_task = asyncio.create_task(heartbeat())
    try:
        await server.serve()
    finally:
        heartbeat_task.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat_task
        await database.engine.dispose()


async def record_worker_heartbeat(
    database,
    *,
    worker_id: str,
    role: str,
    capabilities: list[str],
) -> None:
    async with database.sessions() as session:
        row = await session.get(WorkerTable, worker_id)
        if row is None:
            row = WorkerTable(
                id=worker_id,
                role=role,
                status="online",
                hostname=socket.gethostname(),
                capabilities=capabilities,
                last_seen_at=datetime.now(UTC),
            )
            session.add(row)
        else:
            row.role = role
            row.status = "online"
            row.capabilities = capabilities
            row.last_seen_at = datetime.now(UTC)
        await session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Super Bot worker role")
    parser.add_argument("--role", choices=["worker", "scheduler", "browser"], required=True)
    arguments = parser.parse_args()
    asyncio.run(run_role(arguments.role))


if __name__ == "__main__":
    main()
