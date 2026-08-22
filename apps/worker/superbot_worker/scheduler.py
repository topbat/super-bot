from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import CroniterBadCronError, croniter
from pydantic import BaseModel, field_validator


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
