from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

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
