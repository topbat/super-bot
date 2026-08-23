from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter
from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from sqlalchemy import select

from superbot_api.api.dependencies import SessionDep
from superbot_api.persistence.repositories import NotFoundError
from superbot_api.persistence.tables import BotTable, RoutineTable

router = APIRouter(prefix="/routines", tags=["routines"])


class RoutineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bot_id: UUID
    name: str = Field(min_length=1, max_length=120)
    cron: str = Field(min_length=5, max_length=120)
    timezone: str
    prompt: str = Field(min_length=1, max_length=100_000)
    enabled: bool = True

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


class RoutineRead(RoutineCreate):
    id: UUID
    next_run_at: datetime
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_serializer("next_run_at", "last_run_at", "created_at", "updated_at", when_used="json")
    def serialize_utc_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value
        return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")


@router.post("", response_model=RoutineRead, status_code=status.HTTP_201_CREATED)
async def create_routine(command: RoutineCreate, session: SessionDep) -> RoutineRead:
    if await session.get(BotTable, command.bot_id) is None:
        raise NotFoundError(f"bot {command.bot_id} was not found")
    zone = ZoneInfo(command.timezone)
    next_run = croniter(command.cron, datetime.now(UTC).astimezone(zone)).get_next(datetime)
    row = RoutineTable(**command.model_dump(), next_run_at=next_run.astimezone(UTC))
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return RoutineRead.model_validate(row, from_attributes=True)


@router.get("", response_model=list[RoutineRead])
async def list_routines(session: SessionDep) -> list[RoutineRead]:
    rows = (await session.scalars(select(RoutineTable).order_by(RoutineTable.next_run_at))).all()
    return [RoutineRead.model_validate(row, from_attributes=True) for row in rows]
