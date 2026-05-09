import os

os.environ["ENVIRONMENT"] = "development"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["CORS_ORIGINS"] = "http://test"

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport

from app.core.config import get_settings

get_settings.cache_clear()

import app.models.base as base_module
from app.models.base import Base, get_db

_test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    echo=False,
    connect_args={"check_same_thread": False},
)
_test_session_maker = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)

base_module.engine = _test_engine
base_module.async_session = _test_session_maker


async def _override_get_db():
    async with _test_session_maker() as session:
        yield session


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.seed import seed
    await seed()

    yield

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


def _make_mock_docker():
    mock = MagicMock()
    mock.create_container.return_value = "mock-container-id"
    mock.start_container.return_value = None
    mock.stop_container.return_value = None
    mock.restart_container.return_value = None
    mock.remove_container.return_value = None
    mock.get_container_logs.return_value = ["test log line"]
    mock.get_container_stats.return_value = {"cpu_percent": 1.0, "memory_usage_mb": 100}
    return mock


@pytest.fixture(autouse=True)
def mock_docker():
    mock = _make_mock_docker()
    with patch("app.services.instance_service.DockerAdapter", return_value=mock), \
         patch("app.services.instance_service.os.makedirs"), \
         patch("app.services.instance_service.os.path.exists", return_value=False), \
         patch("builtins.open", MagicMock()):
        yield mock


@pytest.fixture()
async def client():
    from main import app
    app.dependency_overrides[get_db] = _override_get_db

    # Disable rate limiting for tests
    if hasattr(app.state, "limiter"):
        app.state.limiter.enabled = False
    from app.api import auth as auth_module
    auth_module.limiter.enabled = False

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
async def admin_cookies(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.json()["code"] == 0, f"Admin login failed: {resp.json()}"
    return resp.cookies


@pytest.fixture()
async def user_cookies(client: AsyncClient):
    import secrets as _secrets
    username = f"testuser_{_secrets.token_hex(4)}"
    resp = await client.post("/api/auth/register", json={
        "username": username,
        "password": "test123456",
    })
    assert resp.json()["code"] == 0, f"Register failed: {resp.json()}"

    resp = await client.post("/api/auth/login", json={
        "username": username,
        "password": "test123456",
    })
    assert resp.json()["code"] == 0, f"Login failed: {resp.json()}"
    return resp.cookies


@pytest.fixture()
async def second_user_cookies(client: AsyncClient):
    import secrets as _secrets
    username = f"testuser2_{_secrets.token_hex(4)}"
    resp = await client.post("/api/auth/register", json={
        "username": username,
        "password": "test123456",
    })
    assert resp.json()["code"] == 0
    resp = await client.post("/api/auth/login", json={
        "username": username,
        "password": "test123456",
    })
    assert resp.json()["code"] == 0
    return resp.cookies
