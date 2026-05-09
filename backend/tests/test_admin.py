"""Admin API tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_users_admin(client: AsyncClient, admin_cookies):
    resp = await client.get("/api/admin/users", cookies=admin_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["total"] >= 1
    assert any(u["username"] == "admin" for u in data["data"]["items"])


@pytest.mark.asyncio
async def test_list_users_non_admin(client: AsyncClient, user_cookies):
    resp = await client.get("/api/admin/users", cookies=user_cookies)
    data = resp.json()
    assert data["code"] == -3
    assert "无权限" in data["message"]


@pytest.mark.asyncio
async def test_update_user_name(client: AsyncClient, admin_cookies, user_cookies):
    # Get user ID from /me
    me_resp = await client.get("/api/auth/me", cookies=user_cookies)
    user_id = me_resp.json()["data"]["id"]

    resp = await client.put(f"/api/admin/users/{user_id}", json={
        "name": "Updated Name",
    }, cookies=admin_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_user_status(client: AsyncClient, admin_cookies):
    # Register a user to disable
    await client.post("/api/auth/register", json={
        "username": "admin_disable_test",
        "password": "test123456",
    })
    login_resp = await client.post("/api/auth/login", json={
        "username": "admin_disable_test",
        "password": "test123456",
    })
    user_id = login_resp.json()["data"]["user"]["id"]

    resp = await client.put(f"/api/admin/users/{user_id}", json={
        "status": "disabled",
    }, cookies=admin_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["status"] == "disabled"


@pytest.mark.asyncio
async def test_cannot_disable_self(client: AsyncClient, admin_cookies):
    me_resp = await client.get("/api/auth/me", cookies=admin_cookies)
    admin_id = me_resp.json()["data"]["id"]

    resp = await client.put(f"/api/admin/users/{admin_id}", json={
        "status": "disabled",
    }, cookies=admin_cookies)
    data = resp.json()
    assert data["code"] == -4
    assert "自己" in data["message"]


@pytest.mark.asyncio
async def test_reset_password(client: AsyncClient, admin_cookies):
    await client.post("/api/auth/register", json={
        "username": "resetpw_user",
        "password": "oldpass123",
    })
    login_resp = await client.post("/api/auth/login", json={
        "username": "resetpw_user",
        "password": "oldpass123",
    })
    user_id = login_resp.json()["data"]["user"]["id"]

    resp = await client.put(f"/api/admin/users/{user_id}/password", json={
        "new_password": "newpass456",
    }, cookies=admin_cookies)
    assert resp.json()["code"] == 0

    # Login with new password
    login_resp = await client.post("/api/auth/login", json={
        "username": "resetpw_user",
        "password": "newpass456",
    })
    assert login_resp.json()["code"] == 0


@pytest.mark.asyncio
async def test_reset_password_too_short(client: AsyncClient, admin_cookies):
    await client.post("/api/auth/register", json={
        "username": "shortpw_admin",
        "password": "test123456",
    })
    login_resp = await client.post("/api/auth/login", json={
        "username": "shortpw_admin",
        "password": "test123456",
    })
    user_id = login_resp.json()["data"]["user"]["id"]

    resp = await client.put(f"/api/admin/users/{user_id}/password", json={
        "new_password": "abc",
    }, cookies=admin_cookies)
    data = resp.json()
    assert data["code"] == -4
    assert "6" in data["message"]


@pytest.mark.asyncio
async def test_list_audit_logs(client: AsyncClient, admin_cookies):
    resp = await client.get("/api/admin/audit-logs", cookies=admin_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert "items" in data["data"]
    assert "total" in data["data"]


@pytest.mark.asyncio
async def test_admin_list_instances(client: AsyncClient, admin_cookies):
    resp = await client.get("/api/admin/instances", cookies=admin_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert "items" in data["data"]


@pytest.mark.asyncio
@pytest.mark.parametrize("path", [
    "/api/admin/users",
    "/api/admin/instances",
    "/api/admin/audit-logs",
    "/api/admin/settings",
])
async def test_admin_endpoints_reject_non_admin(client: AsyncClient, user_cookies, path):
    resp = await client.get(path, cookies=user_cookies)
    data = resp.json()
    assert data["code"] == -3
