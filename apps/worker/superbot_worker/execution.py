from __future__ import annotations

import asyncio
import hashlib
import mimetypes
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from superbot_api.db import Database
from superbot_api.domain.enums import ApprovalStatus, RiskLevel, TaskEventType, TaskStatus
from superbot_api.domain.models import ArtifactRecord, TaskRead, UsageRecord
from superbot_api.persistence.repositories import ApprovalRepository, TaskRepository
from superbot_api.persistence.tables import BotTable, TaskTable
from superbot_api.policy.engine import PolicyEngine

from superbot_worker.agent.runtime import AgentRuntime, ApprovalRequired, CompletionModel
from superbot_worker.artifacts import ArtifactStore, LocalArtifactStore
from superbot_worker.tools.base import ToolRegistry
from superbot_worker.tools.files import FileReadTool, FileWriteTool
from superbot_worker.tools.http import HttpReadTool


class ExecutionCoordinator:
    """Connect the durable task state machine to the auditable agent runtime."""

    def __init__(
        self,
        *,
        database: Database,
        model: CompletionModel,
        workspace_root: Path,
        artifact_store: ArtifactStore | None = None,
    ) -> None:
        self.database = database
        self.model = model
        self.workspace_root = workspace_root.resolve()
        self.artifact_store = artifact_store or LocalArtifactStore()

    async def execute(self, task_id: UUID, *, user_text: str = "") -> TaskRead:
        async with self.database.sessions() as session:
            task_row, bot_row = await self._load(session, task_id)
            repository = TaskRepository(session)
            approvals = ApprovalRepository(session)

            if task_row.status in {
                TaskStatus.SUCCEEDED.value,
                TaskStatus.FAILED.value,
                TaskStatus.CANCELLED.value,
            }:
                return await repository.get(task_id)
            if task_row.cancel_requested:
                return await repository.update_execution(task_id, status=TaskStatus.CANCELLED)

            checkpoint = task_row.checkpoint
            if checkpoint is None:
                if not user_text.strip():
                    raise ValueError("user_text is required for a new task")
                await repository.update_execution(task_id, status=TaskStatus.RUNNING)
                await repository.append_event(task_id, TaskEventType.STARTED)
            else:
                approval = await approvals.latest_for_task(task_id)
                if approval is None or approval.status is ApprovalStatus.PENDING:
                    return await repository.get(task_id)
                if approval.status is ApprovalStatus.DENIED:
                    await repository.append_event(task_id, TaskEventType.DENIED)
                    failed = await repository.update_execution(task_id, status=TaskStatus.FAILED)
                    await repository.append_event(
                        task_id, TaskEventType.FAILED, {"reason": "approval_denied"}
                    )
                    return failed
                await repository.append_event(task_id, TaskEventType.APPROVED)
                await repository.append_event(
                    task_id,
                    TaskEventType.TOOL_STARTED,
                    {"tool_name": checkpoint["tool_call"]["function"]["name"]},
                )
                await repository.update_execution(
                    task_id,
                    status=TaskStatus.RUNNING,
                    current_step=int(checkpoint["step"]),
                    checkpoint=checkpoint,
                )

            model_id = task_row.model_id or bot_row.model_id
            if not model_id:
                raise ValueError("task has no configured model")
            runtime = self._runtime(
                bot_id=bot_row.id,
                model_id=model_id,
                max_steps=task_row.max_steps,
                fallback_model_ids=bot_row.fallback_model_ids or [],
            )
            try:
                result = await runtime.run(
                    user_text,
                    approved_checkpoint=checkpoint,
                )
            except ApprovalRequired as pause:
                await approvals.create(
                    task_id=task_id,
                    tool_name=pause.tool_name,
                    risk=self._tool_risk(pause.tool_name, bot_row.id),
                    summary=self._approval_summary(pause.tool_name, pause.arguments),
                    arguments=pause.arguments,
                )
                waiting = await repository.update_execution(
                    task_id,
                    status=TaskStatus.WAITING_APPROVAL,
                    current_step=int(pause.checkpoint["step"]),
                    checkpoint=pause.checkpoint,
                )
                await repository.append_event(
                    task_id,
                    TaskEventType.APPROVAL_REQUESTED,
                    {"tool_name": pause.tool_name, "arguments": pause.arguments},
                )
                return waiting
            except Exception as error:
                await repository.update_execution(task_id, status=TaskStatus.FAILED)
                await repository.append_event(
                    task_id,
                    TaskEventType.FAILED,
                    {"error_type": type(error).__name__, "message": str(error)},
                )
                raise

            if checkpoint is not None:
                await repository.append_event(
                    task_id,
                    TaskEventType.TOOL_COMPLETED,
                    {"tool_name": checkpoint["tool_call"]["function"]["name"]},
                )
            await repository.append_event(
                task_id, TaskEventType.MODEL_RESPONSE, {"content": result.content}
            )
            for execution in result.executed_tools:
                if execution.name == "files.write":
                    await self._record_file_artifact(
                        repository, task_id, bot_row.id, execution.arguments["path"]
                    )
            await repository.record_usage(
                UsageRecord(
                    task_id=task_id,
                    model_id=model_id,
                    input_tokens=result.usage.input_tokens,
                    output_tokens=result.usage.output_tokens,
                    cached_tokens=result.usage.cached_tokens,
                    cost_usd=0,
                )
            )
            finished = await repository.update_execution(
                task_id,
                status=TaskStatus.SUCCEEDED,
                current_step=result.steps,
                checkpoint=None,
            )
            await repository.append_event(task_id, TaskEventType.COMPLETED)
            return finished

    async def _load(self, session: AsyncSession, task_id: UUID) -> tuple[TaskTable, BotTable]:
        task = await session.get(TaskTable, task_id)
        if task is None:
            raise LookupError(f"task {task_id} was not found")
        bot = await session.get(BotTable, task.bot_id)
        if bot is None:
            raise LookupError(f"bot {task.bot_id} was not found")
        return task, bot

    def _registry(self, bot_id: UUID) -> ToolRegistry:
        workspace = self.workspace_root / str(bot_id)
        registry = ToolRegistry()
        registry.register(FileReadTool(workspace))
        registry.register(FileWriteTool(workspace))
        registry.register(HttpReadTool())
        return registry

    def _runtime(
        self,
        *,
        bot_id: UUID,
        model_id: str,
        max_steps: int,
        fallback_model_ids: list[str],
    ) -> AgentRuntime:
        return AgentRuntime(
            model=self.model,
            tools=self._registry(bot_id),
            policy=PolicyEngine([]),
            model_id=model_id,
            bot_id=bot_id,
            max_steps=max_steps,
            fallback_model_ids=fallback_model_ids,
            is_cancelled=lambda: False,
        )

    def _tool_risk(self, tool_name: str, bot_id: UUID) -> RiskLevel:
        return self._registry(bot_id).get(tool_name).descriptor.risk

    @staticmethod
    def _approval_summary(tool_name: str, arguments: dict) -> str:
        target = arguments.get("path") or arguments.get("url") or "requested target"
        return f"Allow {tool_name} on {target}"

    async def _record_file_artifact(
        self,
        repository: TaskRepository,
        task_id: UUID,
        bot_id: UUID,
        relative_path: str,
    ) -> None:
        path = (self.workspace_root / str(bot_id) / relative_path).resolve()
        workspace = (self.workspace_root / str(bot_id)).resolve()
        if not path.is_relative_to(workspace):
            raise PermissionError("artifact escaped bot workspace")
        content = await asyncio.to_thread(path.read_bytes)
        storage_key = f"bots/{bot_id}/{Path(relative_path).as_posix()}"
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        await self.artifact_store.put_file(storage_key, path, media_type)
        artifact = ArtifactRecord(
            task_id=task_id,
            name=path.name,
            media_type=media_type,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            storage_key=storage_key,
        )
        await repository.record_artifact(artifact)
        await repository.append_event(
            task_id,
            TaskEventType.ARTIFACT_CREATED,
            {"artifact_id": str(artifact.id), "name": artifact.name},
        )
