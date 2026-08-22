from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from superbot_api.api.dependencies import SessionDep
from superbot_api.domain.enums import ApprovalStatus
from superbot_api.domain.models import ApprovalRecord
from superbot_api.persistence.repositories import ApprovalRepository

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalDecision(BaseModel):
    decision: Literal[ApprovalStatus.APPROVED, ApprovalStatus.DENIED]
    decided_by: str


@router.get("", response_model=list[ApprovalRecord])
async def list_pending_approvals(
    session: SessionDep,
) -> list[ApprovalRecord]:
    return await ApprovalRepository(session).list_pending()


@router.post("/{approval_id}/decision", response_model=ApprovalRecord)
async def decide_approval(
    approval_id: UUID,
    decision: ApprovalDecision,
    session: SessionDep,
) -> ApprovalRecord:
    return await ApprovalRepository(session).decide(
        approval_id, status=decision.decision, decided_by=decision.decided_by
    )
