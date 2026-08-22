from __future__ import annotations

from enum import StrEnum


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskEventType(StrEnum):
    CREATED = "created"
    STARTED = "started"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVED = "approved"
    DENIED = "denied"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    MODEL_RESPONSE = "model_response"
    ARTIFACT_CREATED = "artifact_created"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    LEASE_EXPIRED = "lease_expired"
    RETRY_REQUESTED = "retry_requested"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class RiskLevel(StrEnum):
    READ = "read"
    WRITE = "write"
    SENSITIVE = "sensitive"
    CRITICAL = "critical"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class ExecutionMode(StrEnum):
    LOCAL = "local"
    SANDBOX = "sandbox"
    REMOTE = "remote"


class ProviderKind(StrEnum):
    DASHSCOPE = "dashscope"
    DEEPSEEK = "deepseek"
    MOONSHOT = "moonshot"
    ZHIPU = "zhipu"
    MINIMAX = "minimax"
    SILICONFLOW = "siliconflow"
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


class ToolDecision(StrEnum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"

