from __future__ import annotations

from uuid import uuid4

import pytest
from superbot_api.db import create_database, initialize_schema
from superbot_api.domain.enums import ApprovalStatus, RiskLevel, TaskEventType, TaskStatus
from superbot_api.domain.models import BotCreate, TaskCreate
from superbot_api.persistence.repositories import (
    ApprovalRepository,
    BotRepository,
    ConflictError,
    TaskRepository,
)


@pytest.fixture
async def repositories():
    database = create_database("sqlite+aiosqlite:///:memory:")
    await initialize_schema(database.engine)
    async with database.sessions() as session:
        yield (
            BotRepository(session),
            TaskRepository(session),
            ApprovalRepository(session),
        )
    await database.engine.dispose()


async def test_bot_create_and_list_preserves_operational_fields(repositories) -> None:
    bots, _, _ = repositories

    created = await bots.create(
        BotCreate(
            name="Researcher",
            role="current research",
            description="Cite sources and distinguish facts from inference",
            model_id="qwen3.7-plus",
            daily_budget_usd=2.5,
        )
    )
    listed = await bots.list()

    assert listed == [created]
    assert created.model_id == "qwen3.7-plus"
    assert created.daily_budget_usd == 2.5


async def test_task_creation_is_idempotent(repositories) -> None:
    _, tasks, _ = repositories
    command = TaskCreate(
        bot_id=uuid4(),
        conversation_id=uuid4(),
        message_id=uuid4(),
        idempotency_key="desktop-request-42",
    )

    first = await tasks.create(command)
    second = await tasks.create(command)

    assert second.id == first.id
    assert second.status is TaskStatus.QUEUED


async def test_task_events_are_append_only_and_ordered(repositories) -> None:
    _, tasks, _ = repositories
    task = await tasks.create(
        TaskCreate(bot_id=uuid4(), conversation_id=uuid4(), message_id=uuid4())
    )

    first = await tasks.append_event(task.id, TaskEventType.CREATED, {"source": "desktop"})
    second = await tasks.append_event(task.id, TaskEventType.STARTED, {"worker": "local"})
    events = await tasks.list_events(task.id, after_id=first.id)

    assert [event.id for event in events] == [second.id]
    assert second.id > first.id
    assert second.payload == {"worker": "local"}


async def test_approval_can_only_be_decided_once(repositories) -> None:
    _, tasks, approvals = repositories
    task = await tasks.create(
        TaskCreate(bot_id=uuid4(), conversation_id=uuid4(), message_id=uuid4())
    )
    approval = await approvals.create(
        task_id=task.id,
        tool_name="email.send",
        risk=RiskLevel.SENSITIVE,
        summary="Send one external email",
        arguments={"recipient": "reviewer@example.com"},
    )

    decided = await approvals.decide(
        approval.id, status=ApprovalStatus.APPROVED, decided_by="local-user"
    )

    assert decided.status is ApprovalStatus.APPROVED
    with pytest.raises(ConflictError, match="already decided"):
        await approvals.decide(
            approval.id, status=ApprovalStatus.DENIED, decided_by="local-user"
        )
