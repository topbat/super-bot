from __future__ import annotations

from uuid import UUID, uuid4

from superbot_api.domain.enums import RiskLevel
from superbot_api.domain.models import TaskCreate
from superbot_api.persistence.repositories import ApprovalRepository, TaskRepository


async def test_approval_can_be_listed_and_decided(
    api_client, bot_payload
) -> None:
    bot = (await api_client.post("/api/v1/bots", json=bot_payload)).json()
    database = api_client._transport.app.state.database
    async with database.sessions() as session:
        task = await TaskRepository(session).create(
            TaskCreate(
                bot_id=UUID(bot["id"]),
                conversation_id=uuid4(),
                message_id=uuid4(),
            )
        )
        approval = await ApprovalRepository(session).create(
            task_id=task.id,
            tool_name="files.write",
            risk=RiskLevel.WRITE,
            summary="Write the final report",
            arguments={"path": "report.md"},
        )

    pending = await api_client.get("/api/v1/approvals")
    assert pending.status_code == 200
    assert pending.json()[0]["id"] == str(approval.id)

    decided = await api_client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        json={"decision": "approved", "decided_by": "local-user"},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"

    repeated = await api_client.post(
        f"/api/v1/approvals/{approval.id}/decision",
        json={"decision": "denied", "decided_by": "local-user"},
    )
    assert repeated.status_code == 409
