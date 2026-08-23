from __future__ import annotations

from superbot_api.domain.enums import TaskEventType, TaskStatus


class InvalidTransition(ValueError):
    """Raised when an event is invalid for the current task state."""


_TRANSITIONS: dict[tuple[TaskStatus, TaskEventType], TaskStatus] = {
    (TaskStatus.QUEUED, TaskEventType.STARTED): TaskStatus.RUNNING,
    (TaskStatus.QUEUED, TaskEventType.CANCELLED): TaskStatus.CANCELLED,
    (TaskStatus.RUNNING, TaskEventType.APPROVAL_REQUESTED): TaskStatus.WAITING_APPROVAL,
    (TaskStatus.RUNNING, TaskEventType.COMPLETED): TaskStatus.SUCCEEDED,
    (TaskStatus.RUNNING, TaskEventType.FAILED): TaskStatus.FAILED,
    (TaskStatus.RUNNING, TaskEventType.CANCELLED): TaskStatus.CANCELLED,
    (TaskStatus.RUNNING, TaskEventType.LEASE_EXPIRED): TaskStatus.QUEUED,
    (TaskStatus.WAITING_APPROVAL, TaskEventType.APPROVED): TaskStatus.RUNNING,
    (TaskStatus.WAITING_APPROVAL, TaskEventType.DENIED): TaskStatus.RUNNING,
    (TaskStatus.WAITING_APPROVAL, TaskEventType.CANCELLED): TaskStatus.CANCELLED,
    (TaskStatus.FAILED, TaskEventType.RETRY_REQUESTED): TaskStatus.QUEUED,
}


def transition(current: TaskStatus, event: TaskEventType) -> TaskStatus:
    try:
        return _TRANSITIONS[(current, event)]
    except KeyError as error:
        raise InvalidTransition(f"cannot apply {event} to {current}") from error
