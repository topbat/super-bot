from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from superbot_api.browser_gateway import BrowserGatewayDenied, BrowserGatewayUnavailable
from superbot_api.persistence.repositories import ConflictError, NotFoundError


def problem_response(
    request: Request, *, status: int, slug: str, title: str, detail: str
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": f"https://super-bot.dev/problems/{slug}",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": request.url.path,
            "request_id": request.state.request_id,
        },
    )


async def not_found_handler(request: Request, error: NotFoundError) -> JSONResponse:
    return problem_response(
        request, status=404, slug="not-found", title="Resource not found", detail=str(error)
    )


async def conflict_handler(request: Request, error: ConflictError) -> JSONResponse:
    return problem_response(
        request, status=409, slug="conflict", title="Resource conflict", detail=str(error)
    )


async def validation_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    return problem_response(
        request,
        status=422,
        slug="validation-error",
        title="Request validation failed",
        detail=str(error),
    )


async def browser_unavailable_handler(
    request: Request, error: BrowserGatewayUnavailable
) -> JSONResponse:
    return problem_response(
        request,
        status=503,
        slug="browser-unavailable",
        title="Browser service unavailable",
        detail=str(error),
    )


async def browser_denied_handler(request: Request, error: BrowserGatewayDenied) -> JSONResponse:
    return problem_response(
        request,
        status=403,
        slug="browser-target-denied",
        title="Browser target denied",
        detail=str(error),
    )
