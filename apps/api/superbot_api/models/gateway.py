from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field

from superbot_api.models.capabilities import ModelRequirement
from superbot_api.models.catalog import ModelCatalog


class ModelGatewayError(RuntimeError):
    pass


class ModelUnavailable(ModelGatewayError):
    pass


class ModelProtocolError(ModelGatewayError):
    pass


class SecretResolver(Protocol):
    async def resolve(self, secret_ref: str | None) -> str | None: ...


class EnvironmentSecretResolver:
    async def resolve(self, secret_ref: str | None) -> str | None:
        if secret_ref is None:
            return None
        if not secret_ref.startswith("env:"):
            raise ModelUnavailable(f"unsupported secret reference: {secret_ref.split(':', 1)[0]}")
        variable = secret_ref.removeprefix("env:")
        value = os.environ.get(variable)
        if not value:
            raise ModelUnavailable(f"required provider secret {variable} is not configured")
        return value


class ProviderConfig(BaseModel):
    name: str
    base_url: str
    secret_ref: str | None
    timeout_seconds: float = Field(default=120, gt=0, le=600)
    extra_headers: dict[str, str] = Field(default_factory=dict)


class CompletionRequest(BaseModel):
    messages: list[dict[str, Any]] = Field(min_length=1)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    tool_choice: str = "auto"
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_output_tokens: int | None = Field(default=None, gt=0)
    enable_thinking: bool | None = None


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0


class CompletionResponse(BaseModel):
    model_id: str
    content: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    usage: TokenUsage = Field(default_factory=TokenUsage)
    provider_request_id: str | None = None
    fallback_from: str | None = None


class ModelGateway:
    def __init__(
        self,
        catalog: ModelCatalog,
        providers: dict[str, ProviderConfig],
        secrets: SecretResolver,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.catalog = catalog
        self.providers = providers
        self.secrets = secrets
        self.client = client

    async def complete(
        self,
        model_id: str,
        request: CompletionRequest,
        *,
        fallback_model_ids: Sequence[str] = (),
    ) -> CompletionResponse:
        attempts = [model_id, *fallback_model_ids]
        last_error: ModelUnavailable | None = None
        for candidate in attempts:
            try:
                result = await self._complete_once(candidate, request)
                if candidate != model_id:
                    result.fallback_from = model_id
                return result
            except ModelUnavailable as error:
                last_error = error
        attempted = ", ".join(attempts)
        detail = str(last_error) if last_error else "no model attempts were made"
        raise ModelUnavailable(f"models unavailable ({attempted}): {detail}")

    async def _complete_once(self, model_id: str, request: CompletionRequest) -> CompletionResponse:
        requirement = ModelRequirement(
            tool_calling=bool(request.tools), thinking=request.enable_thinking is True
        )
        model = self.catalog.require(model_id, requirement)
        try:
            provider = self.providers[model.provider]
        except KeyError as error:
            raise ModelUnavailable(
                f"model {model_id} provider {model.provider} is not configured"
            ) from error

        from superbot_api.models.openai_compatible import build_request_body, parse_response

        body = build_request_body(model_id, request, provider=model.provider)
        secret = await self.secrets.resolve(provider.secret_ref)
        headers = {"Content-Type": "application/json", **provider.extra_headers}
        if secret:
            headers["Authorization"] = f"Bearer {secret}"
        url = f"{provider.base_url.rstrip('/')}/chat/completions"
        try:
            if self.client is not None:
                response = await self.client.post(
                    url, json=body, headers=headers, timeout=provider.timeout_seconds
                )
            else:
                async with httpx.AsyncClient(timeout=provider.timeout_seconds) as client:
                    response = await client.post(url, json=body, headers=headers)
        except httpx.HTTPError as error:
            raise ModelUnavailable(
                f"model {model_id} network error: {type(error).__name__}"
            ) from error
        if response.status_code >= 400:
            raise ModelUnavailable(f"model {model_id} returned HTTP {response.status_code}")
        try:
            return parse_response(response.json(), model_id=model_id)
        except (ValueError, TypeError) as error:
            raise ModelProtocolError(f"model {model_id} returned an invalid response") from error
