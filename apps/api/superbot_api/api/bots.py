from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Response, status

from superbot_api.api.dependencies import SessionDep
from superbot_api.domain.enums import TaskEventType
from superbot_api.domain.models import BotCreate, BotRead, MessageCreate, TaskCreate, TaskRead
from superbot_api.persistence.repositories import (
    BotRepository,
    ConversationRepository,
    TaskRepository,
)

router = APIRouter(prefix="/bots", tags=["bots"])


@router.post("", response_model=BotRead, status_code=status.HTTP_201_CREATED)
async def create_bot(command: BotCreate, session: SessionDep) -> BotRead:
    return await BotRepository(session).create(command)


@router.get("", response_model=list[BotRead])
async def list_bots(session: SessionDep) -> list[BotRead]:
    return await BotRepository(session).list()


@router.get("/{bot_id}", response_model=BotRead)
async def get_bot(bot_id: UUID, session: SessionDep) -> BotRead:
    return await BotRepository(session).get(bot_id)


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_bot(bot_id: UUID, session: SessionDep) -> Response:
    await BotRepository(session).archive(bot_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{bot_id}/messages", response_model=TaskRead, status_code=status.HTTP_202_ACCEPTED)
async def send_message(
    bot_id: UUID,
    message: MessageCreate,
    session: SessionDep,
    idempotency_key: Annotated[str | None, Header(max_length=200)] = None,
) -> TaskRead:
    bot = await BotRepository(session).get(bot_id)
    tasks = TaskRepository(session)
    if idempotency_key:
        existing = await tasks.find_by_idempotency_key(bot_id, idempotency_key)
        if existing is not None:
            return existing
    conversation_id, message_id = await ConversationRepository(session).create_with_message(
        bot_id=bot_id,
        content=message.content,
        attachment_ids=message.attachment_ids,
    )
    task = await tasks.create(
        TaskCreate(
            bot_id=bot_id,
            conversation_id=conversation_id,
            message_id=message_id,
            model_id=bot.model_id,
            idempotency_key=idempotency_key,
            max_steps=bot.max_steps,
            budget_usd=bot.daily_budget_usd,
        )
    )
    await tasks.append_event(
        task.id,
        event_type=TaskEventType.CREATED,
        payload={"message_id": str(message_id), "conversation_id": str(conversation_id)},
    )
    return task
