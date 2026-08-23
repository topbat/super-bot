from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import select
from superbot_api.browser_gateway import (
    BrowserGatewayDenied,
    BrowserGatewayUnavailable,
    BrowserSnapshotPayload,
)
from superbot_api.main import create_app
from superbot_api.persistence.tables import BrowserActionTable


class FakeBrowserGateway:
    def __init__(self) -> None:
        self.sessions: set[str] = set()
        self.actions: list[tuple[str, dict[str, object]]] = []
        self.closed: list[str] = []

    def snapshot(self, session_id: str, url: str = "about:blank") -> BrowserSnapshotPayload:
        return BrowserSnapshotPayload(
            session_id=session_id,
            url=url,
            title="Remote page",
            viewport_width=1280,
            viewport_height=720,
            screenshot_base64="iVBORw0KGgo=",
            elements=[],
        )

    async def create(
        self,
        session_id: str,
        *,
        allowed_domains: list[str],
        viewport_width: int,
        viewport_height: int,
    ) -> BrowserSnapshotPayload:
        assert viewport_width == 1280
        assert viewport_height == 720
        assert allowed_domains == ["example.com"]
        self.sessions.add(session_id)
        return self.snapshot(session_id)

    async def perform(self, session_id: str, action: dict[str, object]) -> BrowserSnapshotPayload:
        self.actions.append((session_id, action))
        url = str(action.get("url") or "https://example.com/form")
        return self.snapshot(session_id, url=url)

    async def capture(self, session_id: str) -> BrowserSnapshotPayload:
        return self.snapshot(session_id, url="https://example.com/form")

    async def close(self, session_id: str) -> None:
        self.closed.append(session_id)
        self.sessions.discard(session_id)

    async def aclose(self) -> None:
        return None


@pytest.fixture
async def browser_api(api_database) -> AsyncIterator[tuple[httpx.AsyncClient, FakeBrowserGateway]]:
    gateway = FakeBrowserGateway()
    app = create_app(database=api_database, browser_gateway=gateway)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client, gateway


async def create_bot(client: httpx.AsyncClient, bot_payload: dict) -> str:
    response = await client.post("/api/v1/bots", json=bot_payload)
    assert response.status_code == 201
    return response.json()["id"]


async def test_browser_session_create_navigate_list_snapshot_and_close(
    browser_api, bot_payload
) -> None:
    client, gateway = browser_api
    bot_id = await create_bot(client, bot_payload)

    created = await client.post(
        "/api/v1/browser/sessions",
        json={
            "bot_id": bot_id,
            "start_url": "https://example.com/form",
            "allowed_domains": ["example.com"],
            "viewport_width": 1280,
            "viewport_height": 720,
        },
    )

    assert created.status_code == 201
    body = created.json()
    session_id = body["session"]["id"]
    assert body["session"]["current_url"] == "https://example.com/form"
    assert body["snapshot"]["screenshot_base64"].startswith("iVBOR")
    assert gateway.actions[-1][1] == {
        "kind": "navigate",
        "url": "https://example.com/form",
    }

    listing = await client.get(f"/api/v1/browser/sessions?bot_id={bot_id}")
    assert [item["id"] for item in listing.json()] == [session_id]

    captured = await client.get(f"/api/v1/browser/sessions/{session_id}/snapshot")
    assert captured.status_code == 200
    assert captured.json()["url"] == "https://example.com/form"

    closed = await client.delete(f"/api/v1/browser/sessions/{session_id}")
    assert closed.status_code == 204
    assert gateway.closed == [session_id]


async def test_browser_actions_are_persisted_with_typed_text_redacted(
    browser_api, bot_payload, api_database
) -> None:
    client, _ = browser_api
    bot_id = await create_bot(client, bot_payload)
    created = await client.post(
        "/api/v1/browser/sessions",
        json={"bot_id": bot_id, "allowed_domains": ["example.com"]},
    )
    session_id = created.json()["session"]["id"]

    response = await client.post(
        f"/api/v1/browser/sessions/{session_id}/actions",
        json={"kind": "type", "text": "secret password"},
    )

    assert response.status_code == 200
    async with api_database.sessions() as session:
        row = await session.scalar(select(BrowserActionTable))
    assert row is not None
    assert row.kind == "type"
    assert row.arguments == {"text": "[REDACTED]", "text_length": 15}


async def test_browser_session_requires_existing_bot(browser_api) -> None:
    client, _ = browser_api
    response = await client.post(
        "/api/v1/browser/sessions",
        json={
            "bot_id": "00000000-0000-0000-0000-000000000999",
            "allowed_domains": [],
        },
    )
    assert response.status_code == 404


async def test_browser_gateway_unavailable_returns_service_unavailable(
    api_database, bot_payload
) -> None:
    class UnavailableGateway(FakeBrowserGateway):
        async def create(self, *args, **kwargs) -> BrowserSnapshotPayload:
            raise BrowserGatewayUnavailable("browser gateway offline")

    app = create_app(database=api_database, browser_gateway=UnavailableGateway())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        bot_id = await create_bot(client, bot_payload)
        response = await client.post(
            "/api/v1/browser/sessions",
            json={"bot_id": bot_id, "allowed_domains": []},
        )

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"].endswith("/browser-unavailable")


async def test_denied_start_url_closes_the_ephemeral_remote_session(
    api_database, bot_payload
) -> None:
    class DeniedGateway(FakeBrowserGateway):
        async def perform(self, session_id, action) -> BrowserSnapshotPayload:
            raise BrowserGatewayDenied("private target")

    gateway = DeniedGateway()
    app = create_app(database=api_database, browser_gateway=gateway)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        bot_id = await create_bot(client, bot_payload)
        response = await client.post(
            "/api/v1/browser/sessions",
            json={
                "bot_id": bot_id,
                "start_url": "http://127.0.0.1/admin",
                "allowed_domains": ["example.com"],
            },
        )

    assert response.status_code == 403
    assert len(gateway.closed) == 1
