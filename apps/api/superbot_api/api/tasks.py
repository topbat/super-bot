from __future__ import annotations

import asyncio
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import StreamingResponse

from superbot_api.api.dependencies import SessionDep
from superbot_api.domain.models import TaskRead
from superbot_api.persistence.repositories import TaskRepository

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: UUID, session: SessionDep) -> TaskRead:
    return await TaskRepository(session).get(task_id)


@router.post("/{task_id}/cancel", response_model=TaskRead)
async def cancel_task(task_id: UUID, session: SessionDep) -> TaskRead:
    return await TaskRepository(session).cancel(task_id)


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
