from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from anyio import Path
from redis.asyncio import Redis
from superbot_api.config import get_settings

from superbot_worker.queue import InMemoryDurableQueue, QueueItem


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
        ready_path = Path(f"/tmp/superbot-{role}.ready")
        await ready_path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
        while True:
            await asyncio.sleep(10)
            await redis.ping()
            await ready_path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
    finally:
        await redis.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Super Bot worker role")
    parser.add_argument("--role", choices=["worker", "scheduler", "browser"], required=True)
    arguments = parser.parse_args()
    asyncio.run(run_role(arguments.role))


if __name__ == "__main__":
    main()
