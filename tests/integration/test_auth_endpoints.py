"""Integration tests for authentication endpoints."""

from httpx import AsyncClient


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "password123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email(self, client: AsyncClient, registered_user):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "testuser@example.com",
            "username": "anotheruser",
            "password": "password123",
        })
        assert resp.status_code == 409

    async def test_register_weak_password(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "username": "weakuser",
            "password": "short",
        })
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient, registered_user):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "testuser@example.com",
            "password": "securepassword123",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_login_wrong_password(self, client: AsyncClient, registered_user):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "testuser@example.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "anypassword",
        })
        assert resp.status_code == 401


class TestRefreshAndLogout:
    async def test_refresh_token(self, client: AsyncClient, registered_user):
        refresh_token = registered_user["refresh_token"]
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        # New tokens should be different
        assert data["access_token"] != registered_user["access_token"]

    async def test_logout_and_token_revoked(self, client: AsyncClient, registered_user):
        refresh_token = registered_user["refresh_token"]

        # Logout
        resp = await client.post(
            "/api/v1/auth/logout", json={"refresh_token": refresh_token}
        )
        assert resp.status_code == 204

        # Attempt to use the same refresh token again — should be rejected
        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert resp.status_code == 401

    async def test_access_protected_route_without_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 401
