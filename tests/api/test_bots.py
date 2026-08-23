from __future__ import annotations


async def test_health_and_bot_crud(api_client, bot_payload) -> None:
    health = await api_client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    created = await api_client.post("/api/v1/bots", json=bot_payload)
    assert created.status_code == 201
    bot = created.json()
    assert bot["name"] == "Researcher"

    listing = await api_client.get("/api/v1/bots")
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [bot["id"]]

    fetched = await api_client.get(f"/api/v1/bots/{bot['id']}")
    assert fetched.json()["model_id"] == "qwen3.7-plus"

    archived = await api_client.delete(f"/api/v1/bots/{bot['id']}")
    assert archived.status_code == 204
    assert (await api_client.get("/api/v1/bots")).json() == []


async def test_missing_bot_returns_problem_details(api_client) -> None:
    response = await api_client.get("/api/v1/bots/00000000-0000-0000-0000-000000000999")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"] == "https://super-bot.dev/problems/not-found"
    assert response.json()["request_id"]


async def test_validation_errors_use_problem_details(api_client) -> None:
    response = await api_client.post("/api/v1/bots", json={"name": ""})

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"].endswith("/validation-error")


async def test_models_are_explicit_and_include_domestic_providers(api_client) -> None:
    response = await api_client.get("/api/v1/models")

    assert response.status_code == 200
    ids = {model["id"] for model in response.json()}
    assert {"qwen3.7-plus", "deepseek-chat", "ollama-local"} <= ids
