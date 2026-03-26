"""
Shared test fixtures.

- Uses an in-memory SQLite database via aiosqlite for fast tests.
- Uses fakeredis as a drop-in Redis replacement (no real Redis needed).
- Uses httpx.AsyncClient with ASGITransport (no real HTTP server).
"""

import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import get_async_session
from app.core.redis_client import get_redis
from app.main import app
from app.models.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def session(engine) -> AsyncSession:
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as s:
        yield s
        await s.rollback()


@pytest_asyncio.fixture()
async def fake_redis():
    redis = FakeRedis()
    yield redis
    await redis.flushall()
    await redis.aclose()


@pytest_asyncio.fixture()
async def client(session, fake_redis):
    """Async HTTP test client with dependency overrides."""
    app.dependency_overrides[get_async_session] = lambda: session
    app.dependency_overrides[get_redis] = lambda: fake_redis

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# --- Reusable data fixtures ---

@pytest_asyncio.fixture()
async def registered_user(client):
    """Register a test user and return the response data."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "testuser@example.com",
        "username": "testuser",
        "password": "securepassword123",
    })
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture()
async def auth_headers(registered_user):
    """Return Authorization headers for the registered test user."""
    token = registered_user["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture()
async def test_project(client, auth_headers):
    """Create a test project and return its data."""
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "Test Project", "description": "A test project"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()
