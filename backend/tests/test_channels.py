"""Channel API tests."""
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_platforms(client: AsyncClient, user_cookies):
    resp = await client.get("/api/channels/platforms", cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert "telegram" in data["data"]
    assert "discord" in data["data"]
    assert "weixin" in data["data"]


@pytest.mark.asyncio
async def test_create_channel(client: AsyncClient, user_cookies):
    # Create instance first
    await client.post("/api/instances", json={"name": "ch-inst"}, cookies=user_cookies)

    with patch("app.api.channels._sync_channels_to_container", return_value=None):
        resp = await client.post("/api/channels", json={
            "platform": "telegram",
            "config": {"TELEGRAM_BOT_TOKEN": "123456:ABC-test-token-xyz"},
        }, cookies=user_cookies)

    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["platform"] == "telegram"
    # Token should be masked
    assert "****" in data["data"]["config"]["TELEGRAM_BOT_TOKEN"]


@pytest.mark.asyncio
async def test_create_channel_no_instance(client: AsyncClient, user_cookies):
    resp = await client.post("/api/channels", json={
        "platform": "telegram",
        "config": {"TELEGRAM_BOT_TOKEN": "test-token"},
    }, cookies=user_cookies)
    data = resp.json()
    assert data["code"] == -1
    assert "实例" in data["message"]


@pytest.mark.asyncio
async def test_create_channel_duplicate(client: AsyncClient, user_cookies):
    await client.post("/api/instances", json={"name": "ch-dup-inst"}, cookies=user_cookies)

    with patch("app.api.channels._sync_channels_to_container", return_value=None):
        await client.post("/api/channels", json={
            "platform": "discord",
            "config": {"DISCORD_BOT_TOKEN": "test-discord-token-1234"},
        }, cookies=user_cookies)

        resp = await client.post("/api/channels", json={
            "platform": "discord",
            "config": {"DISCORD_BOT_TOKEN": "test-discord-token-5678"},
        }, cookies=user_cookies)

    data = resp.json()
    assert data["code"] == 409


@pytest.mark.asyncio
async def test_list_channels(client: AsyncClient, user_cookies):
    await client.post("/api/instances", json={"name": "ch-list-inst"}, cookies=user_cookies)

    with patch("app.api.channels._sync_channels_to_container", return_value=None):
        await client.post("/api/channels", json={
            "platform": "telegram",
            "config": {"TELEGRAM_BOT_TOKEN": "test-tg-token-list-1234"},
        }, cookies=user_cookies)

    resp = await client.get("/api/channels", cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1


@pytest.mark.asyncio
async def test_delete_channel(client: AsyncClient, user_cookies):
    await client.post("/api/instances", json={"name": "ch-del-inst"}, cookies=user_cookies)

    with patch("app.api.channels._sync_channels_to_container", return_value=None):
        create_resp = await client.post("/api/channels", json={
            "platform": "slack",
            "config": {
                "SLACK_BOT_TOKEN": "xoxb-test-slack-token-1234",
                "SLACK_APP_TOKEN": "xapp-test-slack-app-1234",
            },
        }, cookies=user_cookies)
        channel_id = create_resp.json()["data"]["id"]

        resp = await client.delete(f"/api/channels/{channel_id}", cookies=user_cookies)
        assert resp.json()["code"] == 0


@pytest.mark.asyncio
async def test_update_channel(client: AsyncClient, user_cookies):
    await client.post("/api/instances", json={"name": "ch-upd-inst"}, cookies=user_cookies)

    with patch("app.api.channels._sync_channels_to_container", return_value=None):
        create_resp = await client.post("/api/channels", json={
            "platform": "telegram",
            "config": {"TELEGRAM_BOT_TOKEN": "test-tg-update-1234"},
        }, cookies=user_cookies)
        channel_id = create_resp.json()["data"]["id"]

        resp = await client.put(f"/api/channels/{channel_id}", json={
            "config": {"TELEGRAM_BOT_TOKEN": "new-tg-token-5678"},
        }, cookies=user_cookies)

    data = resp.json()
    assert data["code"] == 0
