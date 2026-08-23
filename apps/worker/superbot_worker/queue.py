from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ResponseError


@dataclass(slots=True)
class QueueItem:
    id: str
    payload: dict[str, Any]
    leased_by: str | None = None
    lease_expires_at: datetime | None = None


class InMemoryDurableQueue:
    """Deterministic queue double with the same lease rules as deployment."""

    def __init__(self) -> None:
        self._items: dict[str, QueueItem] = {}
        self._order: list[str] = []

    def enqueue(self, item_id: str, payload: dict[str, Any]) -> QueueItem:
        existing = self._items.get(item_id)
        if existing is not None:
            return existing
        item = QueueItem(id=item_id, payload=payload)
        self._items[item_id] = item
        self._order.append(item_id)
        return item

    def lease(
        self,
        worker_id: str,
        *,
        now: datetime | None = None,
        lease_seconds: int = 60,
    ) -> QueueItem | None:
        lease_time = now or datetime.now(UTC)
        for item_id in self._order:
            item = self._items[item_id]
            if item.leased_by is None:
                item.leased_by = worker_id
                item.lease_expires_at = lease_time + timedelta(seconds=lease_seconds)
                return item
        return None

    def heartbeat(
        self,
        item_id: str,
        worker_id: str,
        *,
        now: datetime | None = None,
        lease_seconds: int = 60,
    ) -> None:
        item = self._items[item_id]
        if item.leased_by != worker_id:
            raise PermissionError("only the lease owner can extend a lease")
        item.lease_expires_at = (now or datetime.now(UTC)) + timedelta(seconds=lease_seconds)

    def acknowledge(self, item_id: str, worker_id: str) -> None:
        item = self._items[item_id]
        if item.leased_by != worker_id:
            raise PermissionError("only the lease owner can acknowledge an item")
        del self._items[item_id]
        self._order.remove(item_id)

    def recover_stale(self, *, now: datetime | None = None) -> list[str]:
        recovery_time = now or datetime.now(UTC)
        recovered: list[str] = []
        for item in self._items.values():
            if item.lease_expires_at is not None and item.lease_expires_at <= recovery_time:
                item.leased_by = None
                item.lease_expires_at = None
                recovered.append(item.id)
        return recovered


class RedisStreamQueue:
    """Redis Streams transport; task state remains authoritative in PostgreSQL."""

    def __init__(self, redis: Redis, *, stream: str = "superbot:tasks") -> None:
        self.redis = redis
        self.stream = stream

    async def enqueue(self, item_id: str, payload_json: str) -> str:
        return await self.redis.xadd(self.stream, {"item_id": item_id, "payload": payload_json})

    async def ensure_group(self, group: str) -> None:
        try:
            await self.redis.xgroup_create(self.stream, group, id="0", mkstream=True)
        except ResponseError as error:
            if "BUSYGROUP" not in str(error):
                raise

    async def read(self, group: str, consumer: str, *, block_ms: int = 5_000):
        return await self.redis.xreadgroup(
            group, consumer, {self.stream: ">"}, count=1, block=block_ms
        )

    async def acknowledge(self, group: str, message_id: str) -> int:
        return await self.redis.xack(self.stream, group, message_id)
