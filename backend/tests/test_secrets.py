"""Secrets API tests."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_secret(client: AsyncClient, user_cookies):
    resp = await client.post("/api/secrets", json={
        "name": "My DeepSeek",
        "provider": "deepseek",
        "api_key": "sk-test1234567890",
    }, cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "My DeepSeek"
    assert data["data"]["provider"] == "deepseek"
    assert data["data"]["key_suffix"] == "7890"
    assert "id" in data["data"]


@pytest.mark.asyncio
async def test_list_secrets(client: AsyncClient, user_cookies):
    await client.post("/api/secrets", json={
        "name": "List Test",
        "provider": "openai",
        "api_key": "sk-listtest1234",
    }, cookies=user_cookies)

    resp = await client.get("/api/secrets", cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] >= 1
    assert len(data["data"]["items"]) >= 1


@pytest.mark.asyncio
async def test_update_secret(client: AsyncClient, user_cookies):
    create_resp = await client.post("/api/secrets", json={
        "name": "Update Test",
        "provider": "deepseek",
        "api_key": "sk-update1234",
    }, cookies=user_cookies)
    secret_id = create_resp.json()["data"]["id"]

    resp = await client.put(f"/api/secrets/{secret_id}", json={
        "name": "Updated Name",
        "provider": "openai",
    }, cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "Updated Name"
    assert data["data"]["provider"] == "openai"


@pytest.mark.asyncio
async def test_delete_secret(client: AsyncClient, user_cookies):
    create_resp = await client.post("/api/secrets", json={
        "name": "Delete Test",
        "provider": "deepseek",
        "api_key": "sk-delete1234",
    }, cookies=user_cookies)
    secret_id = create_resp.json()["data"]["id"]

    resp = await client.delete(f"/api/secrets/{secret_id}", cookies=user_cookies)
    assert resp.json()["code"] == 0

    # Verify deleted
    list_resp = await client.get("/api/secrets", cookies=user_cookies)
    ids = [s["id"] for s in list_resp.json()["data"]["items"]]
    assert secret_id not in ids


@pytest.mark.asyncio
async def test_activate_secret(client: AsyncClient, user_cookies):
    # Create an instance first (required for activation)
    await client.post("/api/instances", json={"name": "activate-inst"}, cookies=user_cookies)

    create_resp = await client.post("/api/secrets", json={
        "name": "Activate Test",
        "provider": "deepseek",
        "api_key": "sk-activate1234",
    }, cookies=user_cookies)
    secret_id = create_resp.json()["data"]["id"]

    with patch("app.services.instance_service.DockerAdapter") as mock_cls:
        mock_cls.return_value = MagicMock()
        with patch("app.services.instance_service.update_instance_llm_config", new_callable=AsyncMock):
            resp = await client.post(f"/api/secrets/{secret_id}/activate", cookies=user_cookies)

    assert resp.json()["code"] == 0

    # Verify it's active
    list_resp = await client.get("/api/secrets", cookies=user_cookies)
    for s in list_resp.json()["data"]["items"]:
        if s["id"] == secret_id:
            assert s["is_active"] is True
        else:
            assert s["is_active"] is False


@pytest.mark.asyncio
async def test_secret_ownership(client: AsyncClient, user_cookies, second_user_cookies):
    create_resp = await client.post("/api/secrets", json={
        "name": "Ownership Test",
        "provider": "deepseek",
        "api_key": "sk-own1234",
    }, cookies=user_cookies)
    secret_id = create_resp.json()["data"]["id"]

    # Second user cannot access
    resp = await client.delete(f"/api/secrets/{secret_id}", cookies=second_user_cookies)
    data = resp.json()
    assert data["code"] == -4


@pytest.mark.asyncio
async def test_create_multiple_secrets(client: AsyncClient, user_cookies):
    for i in range(3):
        resp = await client.post("/api/secrets", json={
            "name": f"Multi Test {i}",
            "provider": "deepseek",
            "api_key": f"sk-multi{i}1234",
        }, cookies=user_cookies)
        assert resp.json()["code"] == 0

    list_resp = await client.get("/api/secrets", cookies=user_cookies)
    assert list_resp.json()["data"]["total"] >= 3
