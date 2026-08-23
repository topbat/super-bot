from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from superbot_api.db import Database, create_database, initialize_schema
from superbot_api.main import create_app


@pytest.fixture
async def api_database(tmp_path) -> AsyncIterator[Database]:
    database = create_database(f"sqlite+aiosqlite:///{tmp_path / 'api.sqlite'}")
    await initialize_schema(database.engine)
    yield database
    await database.engine.dispose()


@pytest.fixture
async def api_client(api_database: Database) -> AsyncIterator[httpx.AsyncClient]:
    database = api_database
    app = create_app(database=database)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def bot_payload() -> dict:
    return {
        "name": "Researcher",
        "role": "Research agent",
        "description": "Find and synthesize reliable sources",
        "model_id": "qwen3.7-plus",
        "max_steps": 12,
    }
