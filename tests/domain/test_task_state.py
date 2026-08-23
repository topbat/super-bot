from __future__ import annotations

import pytest
from superbot_api.domain.enums import TaskEventType, TaskStatus
from superbot_api.domain.task_state import InvalidTransition, transition


@pytest.mark.parametrize(
    ("current", "event", "expected"),
    [
        (TaskStatus.QUEUED, TaskEventType.STARTED, TaskStatus.RUNNING),
        (TaskStatus.RUNNING, TaskEventType.APPROVAL_REQUESTED, TaskStatus.WAITING_APPROVAL),
        (TaskStatus.WAITING_APPROVAL, TaskEventType.APPROVED, TaskStatus.RUNNING),
        (TaskStatus.WAITING_APPROVAL, TaskEventType.DENIED, TaskStatus.RUNNING),
        (TaskStatus.RUNNING, TaskEventType.COMPLETED, TaskStatus.SUCCEEDED),
        (TaskStatus.RUNNING, TaskEventType.FAILED, TaskStatus.FAILED),
        (TaskStatus.QUEUED, TaskEventType.CANCELLED, TaskStatus.CANCELLED),
        (TaskStatus.RUNNING, TaskEventType.CANCELLED, TaskStatus.CANCELLED),
        (TaskStatus.RUNNING, TaskEventType.LEASE_EXPIRED, TaskStatus.QUEUED),
        (TaskStatus.FAILED, TaskEventType.RETRY_REQUESTED, TaskStatus.QUEUED),
    ],
)
def test_valid_transitions(current: TaskStatus, event: TaskEventType, expected: TaskStatus) -> None:
    assert transition(current, event) is expected


@pytest.mark.parametrize(
    "terminal",
    [TaskStatus.SUCCEEDED, TaskStatus.CANCELLED],
)
def test_terminal_task_rejects_new_work(terminal: TaskStatus) -> None:
    with pytest.raises(InvalidTransition, match="cannot apply"):
        transition(terminal, TaskEventType.STARTED)


def test_failed_task_only_allows_retry() -> None:
    with pytest.raises(InvalidTransition):
        transition(TaskStatus.FAILED, TaskEventType.COMPLETED)
