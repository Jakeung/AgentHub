"""Instance management API tests."""
import pytest
from unittest.mock import patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_instance(client: AsyncClient, user_cookies):
    resp = await client.post("/api/instances", json={
        "name": "test-hermes",
    }, cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "test-hermes"
    assert "id" in data["data"]
    assert "container_name" in data["data"]
    assert "port" in data["data"]


@pytest.mark.asyncio
async def test_create_instance_duplicate(client: AsyncClient, user_cookies):
    await client.post("/api/instances", json={"name": "dup-inst"}, cookies=user_cookies)
    resp = await client.post("/api/instances", json={"name": "dup-inst-2"}, cookies=user_cookies)
    data = resp.json()
    assert data["code"] != 0


@pytest.mark.asyncio
async def test_list_instances(client: AsyncClient, user_cookies):
    await client.post("/api/instances", json={"name": "list-test"}, cookies=user_cookies)
    resp = await client.get("/api/instances", cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] >= 1
    assert len(data["data"]["items"]) >= 1


@pytest.mark.asyncio
async def test_get_instance(client: AsyncClient, user_cookies):
    create_resp = await client.post("/api/instances", json={"name": "get-test"}, cookies=user_cookies)
    inst_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/api/instances/{inst_id}", cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["id"] == inst_id


@pytest.mark.asyncio
async def test_delete_instance(client: AsyncClient, user_cookies):
    create_resp = await client.post("/api/instances", json={"name": "del-test"}, cookies=user_cookies)
    inst_id = create_resp.json()["data"]["id"]

    resp = await client.delete(f"/api/instances/{inst_id}", cookies=user_cookies)
    assert resp.json()["code"] == 0

    # Should not appear in list
    list_resp = await client.get("/api/instances", cookies=user_cookies)
    ids = [i["id"] for i in list_resp.json()["data"]["items"]]
    assert inst_id not in ids


@pytest.mark.asyncio
async def test_start_instance(client: AsyncClient, user_cookies):
    create_resp = await client.post("/api/instances", json={"name": "start-test"}, cookies=user_cookies)
    inst_id = create_resp.json()["data"]["id"]

    # Set instance to stopped state first
    from app.models.base import get_db
    async for db in _override_get_db():
        from sqlalchemy import select
        from app.models.instance import AgentInstance
        result = await db.execute(select(AgentInstance).where(AgentInstance.id == inst_id))
        inst = result.scalar_one()
        inst.status = "stopped"
        inst.container_id = "mock-container-id"
        await db.commit()

    resp = await client.post(f"/api/instances/{inst_id}/start", cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0


@pytest.mark.asyncio
async def test_stop_instance(client: AsyncClient, user_cookies):
    create_resp = await client.post("/api/instances", json={"name": "stop-test"}, cookies=user_cookies)
    inst_id = create_resp.json()["data"]["id"]

    # Set to running
    async for db in _override_get_db():
        from sqlalchemy import select
        from app.models.instance import AgentInstance
        result = await db.execute(select(AgentInstance).where(AgentInstance.id == inst_id))
        inst = result.scalar_one()
        inst.status = "running"
        inst.container_id = "mock-container-id"
        await db.commit()

    resp = await client.post(f"/api/instances/{inst_id}/stop", cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0


@pytest.mark.asyncio
async def test_restart_instance(client: AsyncClient, user_cookies):
    create_resp = await client.post("/api/instances", json={"name": "restart-test"}, cookies=user_cookies)
    inst_id = create_resp.json()["data"]["id"]

    async for db in _override_get_db():
        from sqlalchemy import select
        from app.models.instance import AgentInstance
        result = await db.execute(select(AgentInstance).where(AgentInstance.id == inst_id))
        inst = result.scalar_one()
        inst.status = "running"
        inst.container_id = "mock-container-id"
        await db.commit()

    resp = await client.post(f"/api/instances/{inst_id}/restart", cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0


@pytest.mark.asyncio
async def test_instance_ownership(client: AsyncClient, user_cookies, second_user_cookies):
    create_resp = await client.post("/api/instances", json={"name": "owner-test"}, cookies=user_cookies)
    inst_id = create_resp.json()["data"]["id"]

    # Second user should not see it
    resp = await client.get(f"/api/instances/{inst_id}", cookies=second_user_cookies)
    data = resp.json()
    assert data["code"] == -4


@pytest.mark.asyncio
async def test_get_logs(client: AsyncClient, user_cookies):
    create_resp = await client.post("/api/instances", json={"name": "logs-test"}, cookies=user_cookies)
    inst_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/api/instances/{inst_id}/logs", cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert "logs" in data["data"]


# Helper: reuse the override from conftest
async def _override_get_db():
    from tests.conftest import _test_session_maker
    async with _test_session_maker() as session:
        yield session
