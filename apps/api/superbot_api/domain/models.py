from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

from superbot_api.domain.enums import (
    ApprovalStatus,
    ExecutionMode,
    MessageRole,
    ProviderKind,
    RiskLevel,
    TaskEventType,
    TaskStatus,
)


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)


class BotCreate(DomainModel):
    name: str = Field(min_length=1, max_length=80)
    role: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=4000)
    model_id: str | None = None
    execution_mode: ExecutionMode = ExecutionMode.SANDBOX
    max_steps: int = Field(default=24, ge=1, le=200)
    daily_budget_usd: float | None = Field(default=None, ge=0)
    fallback_model_ids: list[str] = Field(default_factory=list)

    @field_validator("name", "role", "description")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class BotRead(BotCreate):
    id: UUID
    archived: bool = False
    created_at: datetime
    updated_at: datetime


class ProviderCreate(DomainModel):
    name: str = Field(min_length=1, max_length=80)
    kind: ProviderKind
    base_url: AnyHttpUrl
    secret_ref: str | None = None
    enabled: bool = True

    @field_validator("secret_ref")
    @classmethod
    def secret_must_be_an_external_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        allowed_prefixes = ("env:", "wincred:", "vault:", "file:")
        if not value.startswith(allowed_prefixes):
            raise ValueError("secret_ref must reference an external secret store")
        return value


class ModelCapability(DomainModel):
    text: bool = True
    vision: bool = False
    tool_calling: bool = False
    structured_output: bool = False
    thinking: bool = False
    streaming: bool = True
    context_window: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)


class ModelDefinition(DomainModel):
    id: str = Field(min_length=1, max_length=160)
    provider_id: UUID | None = None
    display_name: str = Field(min_length=1, max_length=160)
    capability: ModelCapability
    input_cost_per_million: float | None = Field(default=None, ge=0)
    output_cost_per_million: float | None = Field(default=None, ge=0)
    enabled: bool = True


class ToolDescriptor(DomainModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_.-]+$")
    description: str = Field(min_length=1, max_length=1000)
    risk: RiskLevel
    input_schema: dict[str, Any]


class MessageCreate(DomainModel):
    role: MessageRole = MessageRole.USER
    content: str = Field(min_length=1, max_length=200_000)
    attachment_ids: list[UUID] = Field(default_factory=list, max_length=6)


class TaskCreate(DomainModel):
    bot_id: UUID
    conversation_id: UUID
    message_id: UUID
    model_id: str | None = None
    parent_task_id: UUID | None = None
    idempotency_key: str | None = Field(default=None, max_length=200)
    max_steps: int = Field(default=24, ge=1, le=200)
    budget_usd: float | None = Field(default=None, ge=0)


class TaskRead(DomainModel):
    id: UUID
    bot_id: UUID
    conversation_id: UUID
    parent_task_id: UUID | None = None
    status: TaskStatus
    model_id: str | None = None
    current_step: int = 0
    max_steps: int = 24
    budget_usd: float | None = None
    spent_usd: float = 0
    created_at: datetime
    updated_at: datetime


class TaskEventRecord(DomainModel):
    id: int
    task_id: UUID
    type: TaskEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ApprovalRecord(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    tool_name: str
    risk: RiskLevel
    summary: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    decided_by: str | None = None
    decided_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ArtifactRecord(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    name: str
    media_type: str
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    storage_key: str
    kind: Literal["input", "output", "screenshot", "trace"] = "output"


class UsageRecord(DomainModel):
    task_id: UUID
    provider_id: UUID | None = None
    model_id: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0, ge=0)
    provider_request_id: str | None = None
