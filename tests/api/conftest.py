from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from superbot_api.db import create_database, initialize_schema
from superbot_api.main import create_app


@pytest.fixture
async def api_client(tmp_path) -> AsyncIterator[httpx.AsyncClient]:
    database = create_database(f"sqlite+aiosqlite:///{tmp_path / 'api.sqlite'}")
    await initialize_schema(database.engine)
    app = create_app(database=database)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    await database.engine.dispose()


@pytest.fixture
def bot_payload() -> dict:
    return {
        "name": "Researcher",
        "role": "Research agent",
        "description": "Find and synthesize reliable sources",
        "model_id": "qwen3.7-plus",
        "max_steps": 12,
    }
