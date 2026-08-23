from __future__ import annotations

import base64

import httpx
import pytest
from superbot_worker.browser import BrowserPolicy, BrowserTargetDenied
from superbot_worker.browser_gateway import (
    BrowserAction,
    BrowserSessionRegistry,
    BrowserSessionUnavailable,
    create_gateway_app,
)


class PublicOnlyPolicy(BrowserPolicy):
    async def validate_resolved(self, url: str) -> str:
        return self.validate(url)


class FakeMouse:
    def __init__(self) -> None:
        self.clicks: list[tuple[int, int]] = []
        self.scrolls: list[tuple[int, int]] = []

    async def click(self, x: int, y: int) -> None:
        self.clicks.append((x, y))

    async def wheel(self, delta_x: int, delta_y: int) -> None:
        self.scrolls.append((delta_x, delta_y))


class FakeKeyboard:
    def __init__(self) -> None:
        self.typed: list[str] = []
        self.pressed: list[str] = []

    async def type(self, text: str) -> None:
        self.typed.append(text)

    async def press(self, key: str) -> None:
        self.pressed.append(key)


class FakePage:
    def __init__(self) -> None:
        self.url = "about:blank"
        self.mouse = FakeMouse()
        self.keyboard = FakeKeyboard()
        self.navigations: list[str] = []
        self.history_actions: list[str] = []

    async def goto(self, url: str, **_: object) -> None:
        self.url = url
        self.navigations.append(url)

    async def title(self) -> str:
        return "Remote page"

    async def screenshot(self, **_: object) -> bytes:
        return b"\x89PNG\r\n\x1a\nremote-browser"

    async def evaluate(self, _: str) -> list[dict[str, object]]:
        return [
            {
                "role": "button",
                "name": "Submit",
                "x": 20,
                "y": 30,
                "width": 80,
                "height": 32,
            }
        ]

    async def go_back(self, **_: object) -> None:
        self.history_actions.append("back")

    async def go_forward(self, **_: object) -> None:
        self.history_actions.append("forward")

    async def reload(self, **_: object) -> None:
        self.history_actions.append("reload")


class FakeContext:
    def __init__(self) -> None:
        self.page = FakePage()
        self.route_pattern: str | None = None
        self.route_handler = None
        self.closed = False

    async def route(self, pattern: str, handler) -> None:
        self.route_pattern = pattern
        self.route_handler = handler

    async def new_page(self) -> FakePage:
        return self.page

    async def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self) -> None:
        self.contexts: list[FakeContext] = []

    async def new_context(self, **options: object) -> FakeContext:
        assert options == {
            "viewport": {"width": 1280, "height": 720},
            "accept_downloads": False,
            "service_workers": "block",
        }
        context = FakeContext()
        self.contexts.append(context)
        return context


class FakeConnector:
    def __init__(self) -> None:
        self.browser = FakeBrowser()

    async def connect(self) -> FakeBrowser:
        return self.browser

    async def close(self) -> None:
        return None


@pytest.fixture
def registry() -> BrowserSessionRegistry:
    return BrowserSessionRegistry(
        connector=FakeConnector(),
        policy_factory=lambda domains: PublicOnlyPolicy(allowed_domains=domains),
    )


async def test_remote_session_navigates_and_returns_png_snapshot(
    registry: BrowserSessionRegistry,
) -> None:
    created = await registry.create(
        "session-1", allowed_domains={"example.com"}, viewport=(1280, 720)
    )
    snapshot = await registry.perform(
        "session-1", BrowserAction(kind="navigate", url="https://example.com/form")
    )

    assert created.session_id == "session-1"
    assert snapshot.url == "https://example.com/form"
    assert snapshot.title == "Remote page"
    assert base64.b64decode(snapshot.screenshot_base64).startswith(b"\x89PNG")
    assert snapshot.elements[0].name == "Submit"


async def test_interactive_actions_target_the_remote_viewport(
    registry: BrowserSessionRegistry,
) -> None:
    await registry.create("session-1", allowed_domains=set(), viewport=(1280, 720))

    await registry.perform("session-1", BrowserAction(kind="click", x=320, y=240))
    await registry.perform("session-1", BrowserAction(kind="type", text="hello world"))
    await registry.perform("session-1", BrowserAction(kind="press", key="Enter"))
    await registry.perform("session-1", BrowserAction(kind="scroll", delta_x=0, delta_y=640))
    await registry.perform("session-1", BrowserAction(kind="back"))
    await registry.perform("session-1", BrowserAction(kind="forward"))
    await registry.perform("session-1", BrowserAction(kind="reload"))

    page = registry.sessions["session-1"].page
    assert page.mouse.clicks == [(320, 240)]
    assert page.keyboard.typed == ["hello world"]
    assert page.keyboard.pressed == ["Enter"]
    assert page.mouse.scrolls == [(0, 640)]
    assert page.history_actions == ["back", "forward", "reload"]


async def test_remote_session_enforces_domain_policy_and_closes_context(
    registry: BrowserSessionRegistry,
) -> None:
    await registry.create("session-1", allowed_domains={"example.com"}, viewport=(1280, 720))

    with pytest.raises(BrowserTargetDenied):
        await registry.perform(
            "session-1",
            BrowserAction(kind="navigate", url="http://127.0.0.1/admin"),
        )

    context = registry.sessions["session-1"].context
    await registry.close("session-1")
    assert context.closed is True
    with pytest.raises(BrowserSessionUnavailable):
        await registry.snapshot("session-1")


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"kind": "navigate"}, "url"),
        ({"kind": "click", "x": -1, "y": 10}, "x"),
        ({"kind": "type", "text": "x" * 20_001}, "text"),
        ({"kind": "press", "key": "x" * 65}, "key"),
        ({"kind": "scroll", "delta_y": 100_001}, "delta_y"),
    ],
)
def test_browser_action_rejects_missing_or_unbounded_arguments(
    payload: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        BrowserAction.model_validate(payload)


async def test_gateway_http_contract_exposes_sessions_actions_and_health(
    registry: BrowserSessionRegistry,
) -> None:
    app = create_gateway_app(registry)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://gateway"
    ) as client:
        health = await client.get("/health")
        created = await client.post(
            "/sessions",
            json={
                "session_id": "session-http",
                "allowed_domains": ["example.com"],
                "viewport_width": 1280,
                "viewport_height": 720,
            },
        )
        navigated = await client.post(
            "/sessions/session-http/actions",
            json={"kind": "navigate", "url": "https://example.com"},
        )
        closed = await client.delete("/sessions/session-http")

    assert health.json() == {"status": "ok", "active_sessions": 0}
    assert created.status_code == 201
    assert navigated.json()["url"] == "https://example.com"
    assert closed.status_code == 204
