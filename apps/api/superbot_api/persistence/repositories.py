from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from superbot_api.domain.enums import ApprovalStatus, RiskLevel, TaskEventType, TaskStatus
from superbot_api.domain.models import (
    ApprovalRecord,
    BotCreate,
    BotRead,
    TaskCreate,
    TaskEventRecord,
    TaskRead,
)
from superbot_api.persistence.tables import ApprovalTable, BotTable, TaskEventTable, TaskTable


class RepositoryError(RuntimeError):
    pass


class NotFoundError(RepositoryError):
    pass


class ConflictError(RepositoryError):
    pass


class BotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, command: BotCreate) -> BotRead:
        row = BotTable(
            name=command.name,
            role=command.role,
            description=command.description,
            model_id=command.model_id,
            execution_mode=command.execution_mode.value,
            max_steps=command.max_steps,
            daily_budget_usd=command.daily_budget_usd,
            fallback_model_ids=command.fallback_model_ids,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return self._to_read(row)

    async def list(self, *, include_archived: bool = False) -> list[BotRead]:
        statement = select(BotTable).order_by(BotTable.created_at, BotTable.id)
        if not include_archived:
            statement = statement.where(BotTable.archived.is_(False))
        rows = (await self.session.scalars(statement)).all()
        return [self._to_read(row) for row in rows]

    async def get(self, bot_id: UUID) -> BotRead:
        row = await self.session.get(BotTable, bot_id)
        if row is None:
            raise NotFoundError(f"bot {bot_id} was not found")
        return self._to_read(row)

    @staticmethod
    def _to_read(row: BotTable) -> BotRead:
        return BotRead(
            id=row.id,
            name=row.name,
            role=row.role,
            description=row.description,
            model_id=row.model_id,
            execution_mode=row.execution_mode,
            max_steps=row.max_steps,
            daily_budget_usd=row.daily_budget_usd,
            fallback_model_ids=row.fallback_model_ids or [],
            archived=row.archived,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, command: TaskCreate) -> TaskRead:
        if command.idempotency_key:
            existing = await self.session.scalar(
                select(TaskTable).where(TaskTable.idempotency_key == command.idempotency_key)
            )
            if existing is not None:
                return self._to_read(existing)
        row = TaskTable(
            bot_id=command.bot_id,
            conversation_id=command.conversation_id,
            message_id=command.message_id,
            parent_task_id=command.parent_task_id,
            model_id=command.model_id,
            max_steps=command.max_steps,
            budget_usd=command.budget_usd,
            idempotency_key=command.idempotency_key,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return self._to_read(row)

    async def get(self, task_id: UUID) -> TaskRead:
        row = await self.session.get(TaskTable, task_id)
        if row is None:
            raise NotFoundError(f"task {task_id} was not found")
        return self._to_read(row)

    async def append_event(
        self, task_id: UUID, event_type: TaskEventType, payload: dict[str, Any] | None = None
    ) -> TaskEventRecord:
        if await self.session.get(TaskTable, task_id) is None:
            raise NotFoundError(f"task {task_id} was not found")
        row = TaskEventTable(task_id=task_id, type=event_type.value, payload=payload or {})
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return self._event_to_read(row)

    async def list_events(self, task_id: UUID, *, after_id: int = 0) -> list[TaskEventRecord]:
        statement = (
            select(TaskEventTable)
            .where(TaskEventTable.task_id == task_id, TaskEventTable.id > after_id)
            .order_by(TaskEventTable.id)
        )
        rows = (await self.session.scalars(statement)).all()
        return [self._event_to_read(row) for row in rows]

    @staticmethod
    def _to_read(row: TaskTable) -> TaskRead:
        return TaskRead(
            id=row.id,
            bot_id=row.bot_id,
            conversation_id=row.conversation_id,
            status=TaskStatus(row.status),
            model_id=row.model_id,
            current_step=row.current_step,
            max_steps=row.max_steps,
            budget_usd=row.budget_usd,
            spent_usd=row.spent_usd,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _event_to_read(row: TaskEventTable) -> TaskEventRecord:
        return TaskEventRecord(
            id=row.id,
            task_id=row.task_id,
            type=TaskEventType(row.type),
            payload=row.payload or {},
            created_at=row.created_at,
        )


class ApprovalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        task_id: UUID,
        tool_name: str,
        risk: RiskLevel,
        summary: str,
        arguments: dict[str, Any],
    ) -> ApprovalRecord:
        row = ApprovalTable(
            task_id=task_id,
            tool_name=tool_name,
            risk=risk.value,
            summary=summary,
            arguments=arguments,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return self._to_read(row)

    async def decide(
        self, approval_id: UUID, *, status: ApprovalStatus, decided_by: str
    ) -> ApprovalRecord:
        if status not in {ApprovalStatus.APPROVED, ApprovalStatus.DENIED}:
            raise ValueError("decision must be approved or denied")
        row = await self.session.get(ApprovalTable, approval_id)
        if row is None:
            raise NotFoundError(f"approval {approval_id} was not found")
        if row.status != ApprovalStatus.PENDING.value:
            raise ConflictError(f"approval {approval_id} was already decided")
        row.status = status.value
        row.decided_by = decided_by
        row.decided_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(row)
        return self._to_read(row)

    async def list_pending(self) -> list[ApprovalRecord]:
        rows = (
            await self.session.scalars(
                select(ApprovalTable)
                .where(ApprovalTable.status == ApprovalStatus.PENDING.value)
                .order_by(ApprovalTable.created_at)
            )
        ).all()
        return [self._to_read(row) for row in rows]

    @staticmethod
    def _to_read(row: ApprovalTable) -> ApprovalRecord:
        return ApprovalRecord(
            id=row.id,
            task_id=row.task_id,
            tool_name=row.tool_name,
            risk=RiskLevel(row.risk),
            summary=row.summary,
            arguments=row.arguments or {},
            status=ApprovalStatus(row.status),
            decided_by=row.decided_by,
            decided_at=row.decided_at,
            created_at=row.created_at,
        )
