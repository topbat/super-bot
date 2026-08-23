from __future__ import annotations

import base64
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, Literal, Protocol

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from superbot_worker.browser import BrowserPolicy, BrowserSession, BrowserTargetDenied


class BrowserSessionUnavailable(LookupError):
    pass


class BrowserGatewayUnavailable(RuntimeError):
    pass


class BrowserAction(BaseModel):
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
    def validate_arguments(self) -> BrowserAction:
        if self.kind == "navigate" and not self.url:
            raise ValueError("url is required for navigate")
        if self.kind == "click" and (self.x is None or self.y is None):
            raise ValueError("x and y are required for click")
        if self.kind == "type" and self.text is None:
            raise ValueError("text is required for type")
        if self.kind == "press" and self.key is None:
            raise ValueError("key is required for press")
        return self


class InteractiveElement(BaseModel):
    role: str
    name: str
    x: float
    y: float
    width: float
    height: float


class BrowserSnapshot(BaseModel):
    session_id: str
    url: str
    title: str
    viewport_width: int
    viewport_height: int
    screenshot_base64: str
    elements: list[InteractiveElement]


class BrowserSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1, max_length=200)
    allowed_domains: list[str] = Field(default_factory=list, max_length=50)
    viewport_width: int = Field(default=1280, ge=800, le=2560)
    viewport_height: int = Field(default=720, ge=600, le=1600)


class BrowserConnector(Protocol):
    async def connect(self) -> Any: ...

    async def close(self) -> None: ...


class PlaywrightConnector:
    def __init__(self, ws_endpoint: str) -> None:
        self.ws_endpoint = ws_endpoint
        self._playwright: Any | None = None
        self._browser: Any | None = None

    async def connect(self) -> Any:
        if self._browser is not None and self._browser.is_connected():
            return self._browser
        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.connect(self.ws_endpoint)
        except Exception as error:
            await self.close()
            raise BrowserGatewayUnavailable("remote Playwright server is unavailable") from error
        return self._browser

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None


class ManagedBrowserSession:
    def __init__(
        self,
        *,
        session_id: str,
        context: Any,
        page: Any,
        policy: BrowserPolicy,
        viewport: tuple[int, int],
    ) -> None:
        self.session_id = session_id
        self.context = context
        self.page = page
        self.policy = policy
        self.viewport = viewport
        self.browser_session = BrowserSession(page, policy, artifact_sink=None)


class BrowserSessionRegistry:
    def __init__(
        self,
        *,
        connector: BrowserConnector,
        policy_factory: Callable[[set[str]], BrowserPolicy] | None = None,
    ) -> None:
        self.connector = connector
        self.policy_factory = policy_factory or (
            lambda domains: BrowserPolicy(allowed_domains=domains)
        )
        self.sessions: dict[str, ManagedBrowserSession] = {}

    async def create(
        self,
        session_id: str,
        *,
        allowed_domains: set[str],
        viewport: tuple[int, int],
    ) -> BrowserSnapshot:
        if session_id in self.sessions:
            raise ValueError(f"browser session {session_id} already exists")
        browser = await self.connector.connect()
        context = await browser.new_context(
            viewport={"width": viewport[0], "height": viewport[1]},
            accept_downloads=False,
            service_workers="block",
        )
        policy = self.policy_factory(allowed_domains)

        async def route_request(route: Any, request: Any) -> None:
            if request.url.startswith(("http://", "https://")):
                try:
                    await policy.validate_resolved(request.url)
                except BrowserTargetDenied:
                    await route.abort("blockedbyclient")
                    return
            elif not request.url.startswith(("about:", "blob:", "data:")):
                await route.abort("blockedbyclient")
                return
            await route.continue_()

        await context.route("**/*", route_request)
        page = await context.new_page()
        self.sessions[session_id] = ManagedBrowserSession(
            session_id=session_id,
            context=context,
            page=page,
            policy=policy,
            viewport=viewport,
        )
        return await self.snapshot(session_id)

    async def perform(self, session_id: str, action: BrowserAction) -> BrowserSnapshot:
        session = self._get(session_id)
        page = session.page
        if action.kind == "navigate":
            assert action.url is not None
            await session.browser_session.navigate(action.url)
        elif action.kind == "click":
            assert action.x is not None and action.y is not None
            await page.mouse.click(action.x, action.y)
        elif action.kind == "type":
            assert action.text is not None
            await page.keyboard.type(action.text)
        elif action.kind == "press":
            assert action.key is not None
            await page.keyboard.press(action.key)
        elif action.kind == "scroll":
            await page.mouse.wheel(action.delta_x, action.delta_y)
        elif action.kind == "back":
            await page.go_back(wait_until="domcontentloaded")
        elif action.kind == "forward":
            await page.go_forward(wait_until="domcontentloaded")
        else:
            await page.reload(wait_until="domcontentloaded")
        if page.url.startswith(("http://", "https://")):
            session.policy.validate(page.url)
        return await self.snapshot(session_id)

    async def snapshot(self, session_id: str) -> BrowserSnapshot:
        session = self._get(session_id)
        screenshot = await session.page.screenshot(type="png")
        elements = await session.page.evaluate(_INTERACTIVE_ELEMENTS_SCRIPT)
        return BrowserSnapshot(
            session_id=session_id,
            url=session.page.url,
            title=await session.page.title(),
            viewport_width=session.viewport[0],
            viewport_height=session.viewport[1],
            screenshot_base64=base64.b64encode(screenshot).decode("ascii"),
            elements=[InteractiveElement.model_validate(element) for element in elements],
        )

    async def close(self, session_id: str) -> None:
        session = self._get(session_id)
        await session.context.close()
        del self.sessions[session_id]

    async def shutdown(self) -> None:
        for session_id in list(self.sessions):
            await self.close(session_id)
        await self.connector.close()

    async def probe(self) -> None:
        await self.connector.connect()

    def _get(self, session_id: str) -> ManagedBrowserSession:
        try:
            return self.sessions[session_id]
        except KeyError as error:
            raise BrowserSessionUnavailable(
                f"browser session {session_id} is not active"
            ) from error


_INTERACTIVE_ELEMENTS_SCRIPT = """
() => Array.from(document.querySelectorAll('a,button,input,textarea,select,[role]'))
  .filter((element) => {
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden';
  })
  .slice(0, 250)
  .map((element) => {
    const rect = element.getBoundingClientRect();
    return {
      role: element.getAttribute('role') || element.tagName.toLowerCase(),
      name:
        element.getAttribute('aria-label') ||
        element.innerText ||
        element.getAttribute('placeholder') ||
        '',
      x: rect.x,
      y: rect.y,
      width: rect.width,
      height: rect.height,
    };
  })
"""


def create_gateway_app(registry: BrowserSessionRegistry) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await registry.shutdown()

    app = FastAPI(title="Super Bot Browser Gateway", lifespan=lifespan)

    @app.exception_handler(BrowserSessionUnavailable)
    async def session_unavailable(_: Request, error: BrowserSessionUnavailable):
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(BrowserTargetDenied)
    async def target_denied(_: Request, error: BrowserTargetDenied):
        return JSONResponse(status_code=403, content={"detail": str(error)})

    @app.exception_handler(BrowserGatewayUnavailable)
    async def gateway_unavailable(_: Request, error: BrowserGatewayUnavailable):
        return JSONResponse(status_code=503, content={"detail": str(error)})

    @app.get("/health")
    async def health() -> dict[str, int | str]:
        await registry.probe()
        return {"status": "ok", "active_sessions": len(registry.sessions)}

    @app.post("/sessions", response_model=BrowserSnapshot, status_code=status.HTTP_201_CREATED)
    async def create_session(command: BrowserSessionCreate) -> BrowserSnapshot:
        return await registry.create(
            command.session_id,
            allowed_domains=set(command.allowed_domains),
            viewport=(command.viewport_width, command.viewport_height),
        )

    @app.get("/sessions/{session_id}/snapshot", response_model=BrowserSnapshot)
    async def snapshot(session_id: str) -> BrowserSnapshot:
        return await registry.snapshot(session_id)

    @app.post("/sessions/{session_id}/actions", response_model=BrowserSnapshot)
    async def perform(session_id: str, action: BrowserAction) -> BrowserSnapshot:
        return await registry.perform(session_id, action)

    @app.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def close(session_id: str) -> Response:
        await registry.close(session_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app
