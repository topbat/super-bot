from __future__ import annotations

from datetime import UTC, datetime

from superbot_api.persistence.tables import WorkerTable


async def test_skill_is_versioned_and_listed(api_client) -> None:
    created = await api_client.post(
        "/api/v1/skills",
        json={
            "name": "primary-research",
            "description": "Research only primary sources",
            "instructions": "Find, verify, and cite primary sources.",
            "tools": ["http.get", "files.write"],
        },
    )

    assert created.status_code == 201
    assert len(created.json()["version"]) == 64
    listing = await api_client.get("/api/v1/skills")
    assert listing.json()[0]["name"] == "primary-research"


async def test_routine_persists_timezone_and_next_run(api_client, bot_payload) -> None:
    bot = (await api_client.post("/api/v1/bots", json=bot_payload)).json()

    created = await api_client.post(
        "/api/v1/routines",
        json={
            "bot_id": bot["id"],
            "name": "Morning brief",
            "cron": "0 9 * * 1-5",
            "timezone": "Asia/Shanghai",
            "prompt": "Create the verified morning brief.",
        },
    )

    assert created.status_code == 201
    assert created.json()["timezone"] == "Asia/Shanghai"
    assert created.json()["next_run_at"].endswith("Z")
    assert (await api_client.get("/api/v1/routines")).json()[0]["name"] == "Morning brief"


async def test_workers_endpoint_reports_persisted_heartbeats(api_client, api_database) -> None:
    async with api_database.sessions() as session:
        session.add(
            WorkerTable(
                id="worker-host:42",
                role="worker",
                status="online",
                hostname="worker-host",
                capabilities=["files", "http"],
                last_seen_at=datetime.now(UTC),
            )
        )
        await session.commit()

    response = await api_client.get("/api/v1/workers")

    assert response.status_code == 200
    assert response.json()[0]["id"] == "worker-host:42"
    assert response.json()[0]["capabilities"] == ["files", "http"]
