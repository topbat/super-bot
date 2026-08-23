from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import CroniterBadCronError, croniter
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from superbot_api.db import Database
from superbot_api.domain.enums import TaskEventType, TaskStatus
from superbot_api.persistence.tables import (
    BotTable,
    ConversationTable,
    MessageTable,
    RoutineTable,
    TaskEventTable,
    TaskTable,
)


class RoutineSchedule(BaseModel):
    cron: str
    timezone: str

    @field_validator("cron")
    @classmethod
    def valid_cron(cls, value: str) -> str:
        if not croniter.is_valid(value):
            raise ValueError("invalid cron expression")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("unknown IANA timezone") from error
        return value

    def next_after(self, instant: datetime) -> datetime:
        if instant.tzinfo is None:
            raise ValueError("scheduler instants must be timezone-aware")
        zone = ZoneInfo(self.timezone)
        try:
            next_local = croniter(self.cron, instant.astimezone(zone)).get_next(datetime)
        except CroniterBadCronError as error:
            raise ValueError("invalid cron expression") from error
        return next_local.astimezone(UTC)


def routine_idempotency_key(routine_id: UUID, occurrence: datetime) -> str:
    if occurrence.tzinfo is None:
        raise ValueError("occurrence must be timezone-aware")
    normalized = occurrence.astimezone(UTC).isoformat(timespec="seconds")
    digest = hashlib.sha256(f"{routine_id}:{normalized}".encode()).hexdigest()
    return f"routine:{routine_id}:{digest[:24]}"


async def dispatch_due_routines(database: Database, *, now: datetime) -> int:
    """Atomically turn every due routine occurrence into one durable task."""
    if now.tzinfo is None:
        raise ValueError("scheduler instants must be timezone-aware")
    dispatched = 0
    async with database.sessions() as session:
        statement = (
            select(RoutineTable)
            .where(
                RoutineTable.enabled.is_(True),
                RoutineTable.next_run_at <= now,
            )
            .order_by(RoutineTable.next_run_at, RoutineTable.id)
            .with_for_update(skip_locked=True)
        )
        rows = (await session.scalars(statement)).all()
        for routine in rows:
            bot = await session.get(BotTable, routine.bot_id)
            occurrence = routine.next_run_at
            if occurrence.tzinfo is None:
                occurrence = occurrence.replace(tzinfo=UTC)
            schedule = RoutineSchedule(cron=routine.cron, timezone=routine.timezone)
            routine.last_run_at = occurrence
            routine.next_run_at = schedule.next_after(occurrence)
            if bot is None or bot.archived:
                routine.enabled = False
                continue

            conversation = ConversationTable(
                bot_id=bot.id,
                title=routine.name,
            )
            session.add(conversation)
            await session.flush()
            message = MessageTable(
                conversation_id=conversation.id,
                role="user",
                content=routine.prompt,
                attachment_ids=[],
            )
            session.add(message)
            await session.flush()
            task = TaskTable(
                bot_id=bot.id,
                conversation_id=conversation.id,
                message_id=message.id,
                status=TaskStatus.QUEUED.value,
                model_id=bot.model_id,
                max_steps=bot.max_steps,
                budget_usd=bot.daily_budget_usd,
                idempotency_key=routine_idempotency_key(routine.id, occurrence),
            )
            session.add(task)
            await session.flush()
            session.add(
                TaskEventTable(
                    task_id=task.id,
                    type=TaskEventType.CREATED.value,
                    payload={
                        "source": "routine",
                        "routine_id": str(routine.id),
                        "scheduled_for": occurrence.isoformat(),
                    },
                )
            )
            dispatched += 1
        await session.commit()
    return dispatched
