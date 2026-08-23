from __future__ import annotations

from contextlib import suppress
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from superbot_api.api.dependencies import SessionDep
from superbot_api.browser_gateway import (
    BrowserGateway,
    BrowserSessionRecord,
    BrowserSnapshotPayload,
)
from superbot_api.persistence.repositories import BrowserSessionRepository

router = APIRouter(prefix="/browser", tags=["browser"])


class BrowserSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bot_id: UUID
    start_url: str | None = Field(default=None, max_length=4096)
    allowed_domains: list[str] = Field(default_factory=list, max_length=50)
    viewport_width: int = Field(default=1280, ge=800, le=2560)
    viewport_height: int = Field(default=720, ge=600, le=1600)

    @field_validator("allowed_domains")
    @classmethod
    def normalize_domains(cls, domains: list[str]) -> list[str]:
        normalized = [domain.casefold().strip().rstrip(".") for domain in domains]
        if any(not domain or "/" in domain or ":" in domain for domain in normalized):
            raise ValueError("allowed domains must be hostnames")
        return list(dict.fromkeys(normalized))


class BrowserActionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["navigate", "click", "type", "press", "scroll", "back", "forward", "reload"]
    url: str | None = Field(default=None, max_length=4096)
    x: int | None = Field(default=None, ge=0, le=10_000)
    y: int | None = Field(default=None, ge=0, le=10_000)
    text: str | None = Field(default=None, max_length=20_000)
    key: str | None = Field(default=None, min_length=1, max_length=64)
    delta_x: int = Field(default=0, ge=-100_000, le=100_000)
    delta_y: int = Field(default=0, ge=-100_000, le=100_000)

    @model_validator(mode="after")
    def validate_arguments(self) -> BrowserActionCreate:
        if self.kind == "navigate" and not self.url:
            raise ValueError("url is required for navigate")
        if self.kind == "click" and (self.x is None or self.y is None):
            raise ValueError("x and y are required for click")
        if self.kind == "type" and self.text is None:
            raise ValueError("text is required for type")
        if self.kind == "press" and self.key is None:
            raise ValueError("key is required for press")
        return self

    def gateway_payload(self) -> dict[str, object]:
        return self.model_dump(exclude_none=True, exclude_unset=True)

    def audit_payload(self) -> dict[str, object]:
        payload = self.gateway_payload()
        if self.kind == "type":
            text = str(payload.pop("text", ""))
            payload["text"] = "[REDACTED]"
            payload["text_length"] = len(text)
        payload.pop("kind", None)
        return payload


class BrowserSessionState(BaseModel):
    session: BrowserSessionRecord
    snapshot: BrowserSnapshotPayload


def gateway(request: Request) -> BrowserGateway:
    return request.app.state.browser_gateway


@router.post("/sessions", response_model=BrowserSessionState, status_code=status.HTTP_201_CREATED)
async def create_browser_session(
    command: BrowserSessionCreate, request: Request, session: SessionDep
) -> BrowserSessionState:
    repository = BrowserSessionRepository(session)
    await repository.require_bot(command.bot_id)
    session_id = uuid4()
    remote = gateway(request)
    remote_created = False
    try:
        snapshot = await remote.create(
            str(session_id),
            allowed_domains=command.allowed_domains,
            viewport_width=command.viewport_width,
            viewport_height=command.viewport_height,
        )
        remote_created = True
        start_action: dict[str, object] | None = None
        if command.start_url:
            start_action = {"kind": "navigate", "url": command.start_url}
            snapshot = await remote.perform(str(session_id), start_action)
        created = await repository.create(
            session_id=session_id,
            bot_id=command.bot_id,
            snapshot=snapshot,
            allowed_domains=command.allowed_domains,
        )
        if start_action is not None:
            await repository.record_action(
                session_id=session_id,
                kind="navigate",
                arguments={"url": command.start_url},
                snapshot=snapshot,
            )
    except Exception:
        if remote_created:
            with suppress(Exception):
                await remote.close(str(session_id))
        raise
    return BrowserSessionState(session=created, snapshot=snapshot)


@router.get("/sessions", response_model=list[BrowserSessionRecord])
async def list_browser_sessions(
    bot_id: UUID, session: SessionDep
) -> list[BrowserSessionRecord]:
    return await BrowserSessionRepository(session).list(bot_id=bot_id)


@router.get("/sessions/{session_id}/snapshot", response_model=BrowserSnapshotPayload)
async def capture_browser_session(
    session_id: UUID, request: Request, session: SessionDep
) -> BrowserSnapshotPayload:
    await BrowserSessionRepository(session).get(session_id)
    return await gateway(request).capture(str(session_id))


@router.post("/sessions/{session_id}/actions", response_model=BrowserSnapshotPayload)
async def perform_browser_action(
    session_id: UUID,
    command: BrowserActionCreate,
    request: Request,
    session: SessionDep,
) -> BrowserSnapshotPayload:
    repository = BrowserSessionRepository(session)
    await repository.get(session_id)
    snapshot = await gateway(request).perform(str(session_id), command.gateway_payload())
    await repository.record_action(
        session_id=session_id,
        kind=command.kind,
        arguments=command.audit_payload(),
        snapshot=snapshot,
    )
    return snapshot


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def close_browser_session(
    session_id: UUID, request: Request, session: SessionDep
) -> Response:
    repository = BrowserSessionRepository(session)
    await repository.get(session_id)
    await gateway(request).close(str(session_id))
    await repository.close(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
