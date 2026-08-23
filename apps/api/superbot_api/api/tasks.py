from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from superbot_api.api.dependencies import SessionDep
from superbot_api.domain.enums import TaskEventType
from superbot_api.domain.models import ArtifactRecord, TaskCreate, TaskRead, UsageRecord
from superbot_api.persistence.repositories import (
    BotRepository,
    ConversationRepository,
    TaskRepository,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


class DelegateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_bot_id: UUID
    prompt: str = Field(min_length=1, max_length=200_000)


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: UUID, session: SessionDep) -> TaskRead:
    return await TaskRepository(session).get(task_id)


@router.post("/{task_id}/cancel", response_model=TaskRead)
async def cancel_task(task_id: UUID, session: SessionDep) -> TaskRead:
    return await TaskRepository(session).cancel(task_id)


@router.post(
    "/{task_id}/delegate",
    response_model=TaskRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def delegate_task(
    task_id: UUID,
    command: DelegateCreate,
    session: SessionDep,
    idempotency_key: Annotated[str | None, Header(max_length=200)] = None,
) -> TaskRead:
    tasks = TaskRepository(session)
    await tasks.get(task_id)
    bot = await BotRepository(session).get(command.target_bot_id)
    delegated_key = None
    if idempotency_key:
        digest = hashlib.sha256(f"{task_id}:{idempotency_key}".encode()).hexdigest()
        delegated_key = f"delegate:{digest}"
        existing = await tasks.find_by_idempotency_key(bot.id, delegated_key)
        if existing is not None:
            return existing
    conversation_id, message_id = await ConversationRepository(session).create_with_message(
        bot_id=bot.id,
        content=command.prompt,
        attachment_ids=[],
    )
    child = await tasks.create(
        TaskCreate(
            bot_id=bot.id,
            conversation_id=conversation_id,
            message_id=message_id,
            parent_task_id=task_id,
            model_id=bot.model_id,
            idempotency_key=delegated_key,
            max_steps=bot.max_steps,
            budget_usd=bot.daily_budget_usd,
        )
    )
    await tasks.append_event(
        child.id,
        TaskEventType.CREATED,
        {"source": "delegation", "parent_task_id": str(task_id)},
    )
    await tasks.append_event(
        task_id,
        TaskEventType.DELEGATED,
        {"child_task_id": str(child.id), "target_bot_id": str(bot.id)},
    )
    return child


@router.get("/{task_id}/artifacts", response_model=list[ArtifactRecord])
async def list_task_artifacts(task_id: UUID, session: SessionDep) -> list[ArtifactRecord]:
    await TaskRepository(session).get(task_id)
    return await TaskRepository(session).list_artifacts(task_id)


@router.get("/{task_id}/usage", response_model=UsageRecord)
async def get_task_usage(task_id: UUID, session: SessionDep) -> UsageRecord:
    await TaskRepository(session).get(task_id)
    return await TaskRepository(session).get_usage(task_id)


@router.get("/{task_id}/events")
async def task_events(
    task_id: UUID,
    request: Request,
    once: bool = Query(default=False),
    last_event_id: Annotated[int | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    database = request.app.state.database
    after_id = last_event_id or 0
    async with database.sessions() as session:
        await TaskRepository(session).get(task_id)

    async def stream():
        nonlocal after_id
        while True:
            async with database.sessions() as session:
                repository = TaskRepository(session)
                events = await repository.list_events(task_id, after_id=after_id)
            for event in events:
                after_id = event.id
                payload = json.dumps(event.payload, ensure_ascii=False, separators=(",", ":"))
                yield f"id: {event.id}\nevent: {event.type.value}\ndata: {payload}\n\n"
            if once:
                break
            yield ": heartbeat\n\n"
            if await request.is_disconnected():
                break
            await asyncio.sleep(15)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
