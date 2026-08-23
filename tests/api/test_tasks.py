from __future__ import annotations


async def create_bot(api_client, bot_payload) -> dict:
    return (await api_client.post("/api/v1/bots", json=bot_payload)).json()


async def test_message_creates_durable_task_idempotently(api_client, bot_payload) -> None:
    bot = await create_bot(api_client, bot_payload)
    request = {"content": "Investigate durable agents"}
    headers = {"Idempotency-Key": "desktop-message-1"}

    first = await api_client.post(
        f"/api/v1/bots/{bot['id']}/messages", json=request, headers=headers
    )
    second = await api_client.post(
        f"/api/v1/bots/{bot['id']}/messages", json=request, headers=headers
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["status"] == "queued"


async def test_idempotency_keys_are_scoped_to_a_bot(api_client, bot_payload) -> None:
    first_bot = await create_bot(api_client, bot_payload)
    second_payload = {**bot_payload, "name": "Writer"}
    second_bot = await create_bot(api_client, second_payload)
    headers = {"Idempotency-Key": "same-desktop-key"}

    first = await api_client.post(
        f"/api/v1/bots/{first_bot['id']}/messages",
        json={"content": "First"},
        headers=headers,
    )
    second = await api_client.post(
        f"/api/v1/bots/{second_bot['id']}/messages",
        json={"content": "Second"},
        headers=headers,
    )

    assert first.status_code == second.status_code == 202
    assert first.json()["id"] != second.json()["id"]


async def test_task_can_be_cancelled_and_emits_replayable_sse(api_client, bot_payload) -> None:
    bot = await create_bot(api_client, bot_payload)
    task = (
        await api_client.post(
            f"/api/v1/bots/{bot['id']}/messages", json={"content": "Stop me"}
        )
    ).json()

    cancelled = await api_client.post(f"/api/v1/tasks/{task['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    stream = await api_client.get(f"/api/v1/tasks/{task['id']}/events?once=true")
    assert stream.status_code == 200
    assert "id: 1" in stream.text
    assert "event: created" in stream.text
    assert "event: cancelled" in stream.text

    replay = await api_client.get(
        f"/api/v1/tasks/{task['id']}/events?once=true",
        headers={"Last-Event-ID": "1"},
    )
    assert "event: created" not in replay.text
    assert "event: cancelled" in replay.text


async def test_task_can_delegate_to_another_bot_idempotently(api_client, bot_payload) -> None:
    coordinator = await create_bot(api_client, bot_payload)
    specialist = await create_bot(api_client, {**bot_payload, "name": "Specialist"})
    parent = (
        await api_client.post(
            f"/api/v1/bots/{coordinator['id']}/messages",
            json={"content": "Coordinate the report"},
        )
    ).json()
    command = {
        "target_bot_id": specialist["id"],
        "prompt": "Verify the model support matrix",
    }
    headers = {"Idempotency-Key": "support-matrix"}

    first = await api_client.post(
        f"/api/v1/tasks/{parent['id']}/delegate", json=command, headers=headers
    )
    second = await api_client.post(
        f"/api/v1/tasks/{parent['id']}/delegate", json=command, headers=headers
    )

    assert first.status_code == second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["bot_id"] == specialist["id"]
    assert first.json()["parent_task_id"] == parent["id"]
    events = await api_client.get(f"/api/v1/tasks/{parent['id']}/events?once=true")
    assert "event: delegated" in events.text
