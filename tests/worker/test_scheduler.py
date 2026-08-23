from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select
from superbot_api.db import create_database, initialize_schema
from superbot_api.persistence.tables import (
    BotTable,
    RoutineTable,
    TaskEventTable,
    TaskTable,
)
from superbot_worker.queue import InMemoryDurableQueue
from superbot_worker.scheduler import (
    RoutineSchedule,
    dispatch_due_routines,
    routine_idempotency_key,
)


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
    assert queue.lease("worker-b", now=now + timedelta(seconds=31), lease_seconds=30).id == "task-1"


@pytest.mark.asyncio
async def test_due_routine_creates_one_auditable_task(tmp_path) -> None:
    database = create_database(f"sqlite+aiosqlite:///{tmp_path / 'scheduler.db'}")
    await initialize_schema(database.engine)
    occurrence = datetime(2026, 8, 24, 1, 0, tzinfo=UTC)
    try:
        async with database.sessions() as session:
            bot = BotTable(
                name="Researcher",
                role="Research agent",
                description="Create verified briefs",
                model_id="qwen3.7-plus",
                max_steps=12,
                daily_budget_usd=1.25,
            )
            session.add(bot)
            await session.flush()
            routine = RoutineTable(
                bot_id=bot.id,
                name="Morning brief",
                cron="0 9 * * 1-5",
                timezone="Asia/Shanghai",
                prompt="Create the verified morning brief.",
                next_run_at=occurrence,
            )
            session.add(routine)
            await session.commit()
            routine_id = routine.id

        assert await dispatch_due_routines(database, now=occurrence) == 1
        assert await dispatch_due_routines(database, now=occurrence) == 0

        async with database.sessions() as session:
            tasks = (await session.scalars(select(TaskTable))).all()
            events = (await session.scalars(select(TaskEventTable))).all()
            routine = await session.get(RoutineTable, routine_id)

        assert len(tasks) == 1
        assert tasks[0].idempotency_key == routine_idempotency_key(routine_id, occurrence)
        assert tasks[0].model_id == "qwen3.7-plus"
        assert events[0].type == "created"
        assert events[0].payload["source"] == "routine"
        assert routine is not None
        assert routine.last_run_at is not None
        assert routine.next_run_at > occurrence.replace(tzinfo=None)
    finally:
        await database.engine.dispose()
