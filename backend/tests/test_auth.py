"""Auth API tests."""
import pytest
from datetime import datetime, timezone, timedelta
from jose import jwt
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "username": "newuser_reg",
        "password": "pass123456",
        "email": "newuser_reg@test.com",
    })
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["username"] == "newuser_reg"
    assert "id" in data["data"]


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "username": "dupuser",
        "password": "pass123456",
    })
    resp = await client.post("/api/auth/register", json={
        "username": "dupuser",
        "password": "pass123456",
    })
    data = resp.json()
    assert data["code"] == -1
    assert "已存在" in data["message"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "username": "emailuser1",
        "password": "pass123456",
        "email": "dup@test.com",
    })
    resp = await client.post("/api/auth/register", json={
        "username": "emailuser2",
        "password": "pass123456",
        "email": "dup@test.com",
    })
    data = resp.json()
    assert data["code"] == -1
    assert "邮箱" in data["message"]


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "username": "shortpw",
        "password": "abc",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "username": "loginuser",
        "password": "pass123456",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "loginuser",
        "password": "pass123456",
    })
    data = resp.json()
    assert data["code"] == 0
    assert "user" in data["data"]
    assert data["data"]["user"]["username"] == "loginuser"
    assert "permissions" in data["data"]
    assert "auth-token" in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "username": "wrongpw_user",
        "password": "pass123456",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "wrongpw_user",
        "password": "wrongpass",
    })
    data = resp.json()
    assert data["code"] == -1
    assert "密码错误" in data["message"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={
        "username": "nonexistent_user_xyz",
        "password": "pass123456",
    })
    data = resp.json()
    assert data["code"] == -1


@pytest.mark.asyncio
async def test_login_disabled_account(client: AsyncClient, admin_cookies):
    # Register a user
    await client.post("/api/auth/register", json={
        "username": "disableduser",
        "password": "pass123456",
    })
    # Login to get user id
    resp = await client.post("/api/auth/login", json={
        "username": "disableduser",
        "password": "pass123456",
    })
    user_id = resp.json()["data"]["user"]["id"]

    # Admin disables the user
    await client.put(f"/api/admin/users/{user_id}", json={
        "status": "disabled",
    }, cookies=admin_cookies)

    # Try login again
    resp = await client.post("/api/auth/login", json={
        "username": "disableduser",
        "password": "pass123456",
    })
    data = resp.json()
    assert data["code"] == -1
    assert "禁用" in data["message"]


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, user_cookies):
    resp = await client.post("/api/auth/logout", cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0
    cookie_header = resp.headers.get("set-cookie", "")
    assert "auth-token" in cookie_header


@pytest.mark.asyncio
async def test_me_authenticated(client: AsyncClient, user_cookies):
    resp = await client.get("/api/auth/me", cookies=user_cookies)
    data = resp.json()
    assert data["code"] == 0
    assert "username" in data["data"]
    assert "permissions" in data["data"]
    assert isinstance(data["data"]["permissions"], list)


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    data = resp.json()
    assert data["code"] == -2
    assert "未登录" in data["message"]


@pytest.mark.asyncio
async def test_me_expired_token(client: AsyncClient):
    from app.core.config import get_settings
    settings = get_settings()
    expired_payload = {
        "id": 999,
        "username": "expired",
        "role": "user",
        "permissions": [],
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    client.cookies.set("auth-token", expired_token)
    resp = await client.get("/api/auth/me")
    data = resp.json()
    assert data["code"] == -2
    assert "过期" in data["message"]
