"""Integration tests for project endpoints."""

from httpx import AsyncClient


class TestProjectCRUD:
    async def test_create_project(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/v1/projects/",
            json={"name": "My Project", "description": "Test"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Project"
        assert "id" in data

    async def test_list_projects_includes_own(
        self, client: AsyncClient, auth_headers, test_project
    ):
        resp = await client.get("/api/v1/projects/", headers=auth_headers)
        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()]
        assert test_project["id"] in ids

    async def test_get_project_detail(
        self, client: AsyncClient, auth_headers, test_project
    ):
        resp = await client.get(
            f"/api/v1/projects/{test_project['id']}", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == test_project["name"]
        assert "members" in data

    async def test_update_project(
        self, client: AsyncClient, auth_headers, test_project
    ):
        resp = await client.patch(
            f"/api/v1/projects/{test_project['id']}",
            json={"name": "Updated Name"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    async def test_delete_project(self, client: AsyncClient, auth_headers):
        # Create a project specifically for deletion
        create_resp = await client.post(
            "/api/v1/projects/",
            json={"name": "To Delete"},
            headers=auth_headers,
        )
        project_id = create_resp.json()["id"]

        del_resp = await client.delete(
            f"/api/v1/projects/{project_id}", headers=auth_headers
        )
        assert del_resp.status_code == 204

        get_resp = await client.get(
            f"/api/v1/projects/{project_id}", headers=auth_headers
        )
        assert get_resp.status_code in (403, 404)

    async def test_cannot_access_other_user_project(
        self, client: AsyncClient, test_project
    ):
        # Register a second user
        resp = await client.post("/api/v1/auth/register", json={
            "email": "other@example.com",
            "username": "otheruser",
            "password": "password123",
        })
        other_token = resp.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        resp = await client.get(
            f"/api/v1/projects/{test_project['id']}", headers=other_headers
        )
        assert resp.status_code == 403


class TestProjectMembers:
    async def test_owner_is_in_members_list(
        self, client: AsyncClient, auth_headers, test_project
    ):
        resp = await client.get(
            f"/api/v1/projects/{test_project['id']}/members", headers=auth_headers
        )
        assert resp.status_code == 200
        roles = [m["role"] for m in resp.json()]
        assert "owner" in roles
