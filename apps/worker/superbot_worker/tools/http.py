from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlsplit

import httpx
from superbot_api.domain.enums import RiskLevel
from superbot_api.domain.models import ToolDescriptor

from superbot_worker.tools.base import ToolResult


class UnsafeNetworkTarget(PermissionError):
    pass


def validate_public_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeNetworkTarget("only absolute HTTP(S) URLs are allowed")
    try:
        address = ip_address(parsed.hostname)
    except ValueError:
        return
    if not address.is_global:
        raise UnsafeNetworkTarget("private, local, reserved, and metadata IPs are blocked")


class HttpReadTool:
    descriptor = ToolDescriptor(
        name="http.get",
        description="Fetch a public HTTP(S) resource without following redirects",
        risk=RiskLevel.READ,
        input_schema={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
            "additionalProperties": False,
        },
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client

    async def execute(self, arguments: dict) -> ToolResult:
        url = str(arguments["url"])
        validate_public_url(url)
        if self.client is not None:
            response = await self.client.get(url, follow_redirects=False)
        else:
            async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
                response = await client.get(url)
        response.raise_for_status()
        return ToolResult(
            ok=True,
            content=response.text,
            metadata={
                "url": str(response.url),
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
            },
        )
