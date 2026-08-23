from __future__ import annotations

import hashlib
import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from superbot_api.api.dependencies import SessionDep
from superbot_api.persistence.tables import SkillTable

router = APIRouter(prefix="/skills", tags=["skills"])


class SkillCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    description: str = Field(min_length=3, max_length=500)
    instructions: str = Field(min_length=1, max_length=100_000)
    tools: list[str] = Field(default_factory=list)


class SkillRead(SkillCreate):
    id: UUID
    version: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


@router.post("", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
async def create_skill(command: SkillCreate, session: SessionDep) -> SkillRead:
    canonical = json.dumps(command.model_dump(), sort_keys=True, separators=(",", ":"))
    row = SkillTable(**command.model_dump(), version=hashlib.sha256(canonical.encode()).hexdigest())
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return SkillRead.model_validate(row, from_attributes=True)


@router.get("", response_model=list[SkillRead])
async def list_skills(session: SessionDep) -> list[SkillRead]:
    rows = (await session.scalars(select(SkillTable).order_by(SkillTable.name))).all()
    return [SkillRead.model_validate(row, from_attributes=True) for row in rows]
