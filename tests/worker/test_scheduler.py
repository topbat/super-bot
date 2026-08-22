from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from superbot_worker.queue import InMemoryDurableQueue
from superbot_worker.scheduler import RoutineSchedule, routine_idempotency_key


def test_routine_uses_declared_timezone() -> None:
    routine = RoutineSchedule(cron="0 9 * * 1-5", timezone="Asia/Shanghai")

    next_run = routine.next_after(datetime(2026, 8, 23, 0, 0, tzinfo=UTC))

    assert next_run == datetime(2026, 8, 24, 1, 0, tzinfo=UTC)


def test_routine_idempotency_key_is_stable_per_occurrence() -> None:
    routine_id = UUID("00000000-0000-0000-0000-000000000008")
    occurrence = datetime(2026, 8, 24, 1, 0, tzinfo=UTC)

    assert routine_idempotency_key(routine_id, occurrence) == routine_idempotency_key(
        routine_id, occurrence
    )
    assert routine_idempotency_key(routine_id, occurrence) != routine_idempotency_key(
        routine_id, occurrence + timedelta(days=1)
    )


def test_stale_queue_lease_is_recovered() -> None:
    queue = InMemoryDurableQueue()
    now = datetime(2026, 8, 23, 10, 0, tzinfo=UTC)
    queue.enqueue("task-1", {"task_id": "task-1"})
    leased = queue.lease("worker-a", now=now, lease_seconds=30)

    assert leased is not None
    assert queue.lease("worker-b", now=now, lease_seconds=30) is None
    recovered = queue.recover_stale(now=now + timedelta(seconds=31))

    assert recovered == ["task-1"]
    assert queue.lease(
        "worker-b", now=now + timedelta(seconds=31), lease_seconds=30
    ).id == "task-1"
