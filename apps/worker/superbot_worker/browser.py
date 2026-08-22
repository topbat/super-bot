from __future__ import annotations

import asyncio
import socket
from ipaddress import ip_address
from urllib.parse import urlsplit, urlunsplit


class BrowserTargetDenied(PermissionError):
    pass


class BrowserPolicy:
    def __init__(self, *, allowed_domains: set[str] | None = None) -> None:
        self.allowed_domains = {
            domain.casefold().rstrip(".") for domain in allowed_domains or set()
        }

    def validate(self, url: str) -> str:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").casefold().rstrip(".")
        if parsed.scheme not in {"http", "https"} or not host:
            raise BrowserTargetDenied("browser navigation requires an HTTP(S) URL")
        if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
            raise BrowserTargetDenied("local hostnames are blocked")
        try:
            address = ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise BrowserTargetDenied("private, local, reserved, and metadata IPs are blocked")
        if self.allowed_domains and host not in self.allowed_domains:
            raise BrowserTargetDenied("domain is not in this bot's allowlist")
        return urlunsplit(parsed)

    async def validate_resolved(self, url: str) -> str:
        validated = self.validate(url)
        host = urlsplit(validated).hostname
        assert host is not None
        try:
            addresses = await asyncio.to_thread(
                socket.getaddrinfo, host, None, type=socket.SOCK_STREAM
            )
        except socket.gaierror as error:
            raise BrowserTargetDenied("target hostname cannot be resolved") from error
        for result in addresses:
            address = ip_address(result[4][0])
            if not address.is_global:
                raise BrowserTargetDenied("target DNS resolved to a blocked address")
        return validated


class BrowserSession:
    """Policy gate around an injected browser page with audit artifact hooks."""

    def __init__(self, page, policy: BrowserPolicy, artifact_sink) -> None:
        self.page = page
        self.policy = policy
        self.artifact_sink = artifact_sink

    async def navigate(self, url: str) -> None:
        await self.page.goto(await self.policy.validate_resolved(url))
        self.policy.validate(self.page.url)

    async def capture(self, name: str) -> None:
        screenshot = await self.page.screenshot(full_page=True)
        await self.artifact_sink(name, screenshot, "image/png")
