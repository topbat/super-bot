from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from superbot_api.api import approvals, bots, models, routines, skills, tasks, workers
from superbot_api.api.errors import conflict_handler, not_found_handler, validation_handler
from superbot_api.config import get_settings
from superbot_api.db import Database, create_database, initialize_schema
from superbot_api.persistence.repositories import ConflictError, NotFoundError


def create_app(*, database: Database | None = None) -> FastAPI:
    selected_database = database or create_database(get_settings().database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await initialize_schema(selected_database.engine)
        yield
        if database is None:
            await selected_database.engine.dispose()

    settings = get_settings()
    app = FastAPI(title="Super Bot API", version="0.1.0", lifespan=lifespan)
    app.state.database = selected_database
    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(ConflictError, conflict_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID") or str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    for router in (
        bots.router,
        tasks.router,
        approvals.router,
        models.router,
        skills.router,
        routines.router,
        workers.router,
    ):
        app.include_router(router, prefix="/api/v1")
    return app


app = create_app()
