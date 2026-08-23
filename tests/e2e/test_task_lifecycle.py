from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from superbot_api.db import create_database, initialize_schema
from superbot_api.domain.enums import ApprovalStatus, TaskEventType, TaskStatus
from superbot_api.domain.models import BotCreate, TaskCreate
from superbot_api.models.gateway import CompletionResponse, TokenUsage
from superbot_api.persistence.repositories import ApprovalRepository, BotRepository, TaskRepository
from superbot_worker.execution import ExecutionCoordinator


class ApprovalThenResultModel:
    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, model_id, request, *, fallback_model_ids=()):
        self.calls += 1
        if self.calls == 1:
            return CompletionResponse(
                model_id=model_id,
                content="",
                tool_calls=[
                    {
                        "id": "write-1",
                        "type": "function",
                        "function": {
                            "name": "files.write",
                            "arguments": '{"path":"result.md","content":"verified result"}',
                        },
                    }
                ],
                usage=TokenUsage(input_tokens=20, output_tokens=8),
            )
        return CompletionResponse(
            model_id=model_id,
            content="报告已生成。",
            usage=TokenUsage(input_tokens=12, output_tokens=6),
        )


async def test_full_task_approval_artifact_audit_and_usage_lifecycle(tmp_path: Path) -> None:
    database = create_database(f"sqlite+aiosqlite:///{tmp_path / 'e2e.sqlite'}")
    await initialize_schema(database.engine)
    bot_id: UUID
    task_id: UUID
    async with database.sessions() as session:
        bot = await BotRepository(session).create(
            BotCreate(
                name="Delivery Bot",
                role="Writer",
                description="Produces reviewed files",
                model_id="qwen3.7-plus",
            )
        )
        bot_id = bot.id
        task = await TaskRepository(session).create(
            TaskCreate(
                bot_id=bot.id,
                conversation_id=uuid4(),
                message_id=uuid4(),
                model_id=bot.model_id,
            )
        )
        task_id = task.id
        await TaskRepository(session).append_event(task.id, TaskEventType.CREATED)

    coordinator = ExecutionCoordinator(
        database=database,
        model=ApprovalThenResultModel(),
        workspace_root=tmp_path / "workspaces",
    )

    paused = await coordinator.execute(task_id, user_text="Create a verified report")
    assert paused.status is TaskStatus.WAITING_APPROVAL

    async with database.sessions() as session:
        pending = await ApprovalRepository(session).list_pending()
        assert len(pending) == 1
        assert pending[0].arguments["path"] == "result.md"
        await ApprovalRepository(session).decide(
            pending[0].id,
            status=ApprovalStatus.APPROVED,
            decided_by="e2e-user",
        )

    finished = await coordinator.execute(task_id)

    assert finished.status is TaskStatus.SUCCEEDED
    assert (tmp_path / "workspaces" / str(bot_id) / "result.md").read_text(
        encoding="utf-8"
    ) == "verified result"
    async with database.sessions() as session:
        repository = TaskRepository(session)
        events = await repository.list_events(task_id)
        artifacts = await repository.list_artifacts(task_id)
        usage = await repository.get_usage(task_id)

    assert [event.type for event in events] == [
        TaskEventType.CREATED,
        TaskEventType.STARTED,
        TaskEventType.APPROVAL_REQUESTED,
        TaskEventType.APPROVED,
        TaskEventType.TOOL_STARTED,
        TaskEventType.TOOL_COMPLETED,
        TaskEventType.MODEL_RESPONSE,
        TaskEventType.ARTIFACT_CREATED,
        TaskEventType.COMPLETED,
    ]
    assert artifacts[0].name == "result.md"
    assert artifacts[0].sha256 == "218873640bdfd1d86ff1abac2d0bcf332b89dd879c6a57dda512b5811f303173"
    assert usage.input_tokens == 32
    assert usage.output_tokens == 14
    await database.engine.dispose()
