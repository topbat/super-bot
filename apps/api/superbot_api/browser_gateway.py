from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

import httpx
from pydantic import BaseModel


class BrowserGatewayUnavailable(RuntimeError):
    pass


class BrowserGatewayDenied(PermissionError):
    pass


class InteractiveElementPayload(BaseModel):
    role: str
    name: str
    x: float
    y: float
    width: float
    height: float


class BrowserSnapshotPayload(BaseModel):
    session_id: str
    url: str
    title: str
    viewport_width: int
    viewport_height: int
    screenshot_base64: str
    elements: list[InteractiveElementPayload]


class BrowserSessionRecord(BaseModel):
    id: UUID
    bot_id: UUID
    status: str
    current_url: str
    title: str
    allowed_domains: list[str]
    viewport_width: int
    viewport_height: int
    created_at: datetime
    updated_at: datetime


class BrowserGateway(Protocol):
    async def create(
        self,
        session_id: str,
        *,
        allowed_domains: list[str],
        viewport_width: int,
        viewport_height: int,
    ) -> BrowserSnapshotPayload: ...

    async def perform(
        self, session_id: str, action: dict[str, object]
    ) -> BrowserSnapshotPayload: ...

    async def capture(self, session_id: str) -> BrowserSnapshotPayload: ...

    async def close(self, session_id: str) -> None: ...

    async def aclose(self) -> None: ...


class HttpBrowserGatewayClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 30.0) -> None:
        self.client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout_seconds)

    async def create(
        self,
        session_id: str,
        *,
        allowed_domains: list[str],
        viewport_width: int,
        viewport_height: int,
    ) -> BrowserSnapshotPayload:
        return await self._request(
            "POST",
            "/sessions",
            json={
                "session_id": session_id,
                "allowed_domains": allowed_domains,
                "viewport_width": viewport_width,
                "viewport_height": viewport_height,
            },
        )

    async def perform(self, session_id: str, action: dict[str, object]) -> BrowserSnapshotPayload:
        return await self._request("POST", f"/sessions/{session_id}/actions", json=action)

    async def capture(self, session_id: str) -> BrowserSnapshotPayload:
        return await self._request("GET", f"/sessions/{session_id}/snapshot")

    async def close(self, session_id: str) -> None:
        await self._request("DELETE", f"/sessions/{session_id}", expect_json=False)

    async def aclose(self) -> None:
        await self.client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        expect_json: bool = True,
    ) -> BrowserSnapshotPayload | None:
        try:
            response = await self.client.request(method, path, json=json)
        except httpx.HTTPError as error:
            raise BrowserGatewayUnavailable("browser gateway is unreachable") from error
        if response.status_code == 403:
            raise BrowserGatewayDenied(response.text)
        if response.status_code == 404:
            raise BrowserGatewayUnavailable("remote browser session is unavailable")
        if response.is_error:
            raise BrowserGatewayUnavailable(f"browser gateway returned HTTP {response.status_code}")
        if not expect_json:
            return None
        return BrowserSnapshotPayload.model_validate(response.json())
