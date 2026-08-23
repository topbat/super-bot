from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from superbot_api.api.dependencies import SessionDep
from superbot_api.persistence.tables import WorkerTable

router = APIRouter(prefix="/workers", tags=["workers"])


class WorkerRead(BaseModel):
    id: str
    role: str
    status: str
    hostname: str
    capabilities: list[str]
    last_seen_at: datetime


@router.get("", response_model=list[WorkerRead])
async def list_workers(session: SessionDep) -> list[WorkerRead]:
    rows = (
        await session.scalars(select(WorkerTable).order_by(WorkerTable.id))
    ).all()
    stale_before = datetime.now(UTC) - timedelta(seconds=30)
    result = []
    for row in rows:
        last_seen = row.last_seen_at
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=UTC)
        result.append(
            WorkerRead(
                id=row.id,
                role=row.role,
                status="offline" if last_seen < stale_before else row.status,
                hostname=row.hostname,
                capabilities=row.capabilities or [],
                last_seen_at=last_seen,
            )
        )
    return result
