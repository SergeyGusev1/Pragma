"""Integration tests for task endpoints."""

import pytest
from httpx import AsyncClient


class TestTaskCRUD:
    async def test_create_task(self, client: AsyncClient, auth_headers, test_project):
        resp = await client.post(
            f"/api/v1/projects/{test_project['id']}/tasks",
            json={
                "title": "Write tests",
                "description": "Cover all endpoints",
                "priority": "high",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Write tests"
        assert data["status"] == "todo"
        assert data["priority"] == "high"

    async def test_list_tasks(self, client: AsyncClient, auth_headers, test_project):
        # Create a task first
        await client.post(
            f"/api/v1/projects/{test_project['id']}/tasks",
            json={"title": "Task A"},
            headers=auth_headers,
        )
        resp = await client.get(
            f"/api/v1/projects/{test_project['id']}/tasks", headers=auth_headers
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 1

    async def test_filter_tasks_by_status(self, client: AsyncClient, auth_headers, test_project):
        # Create a task and update its status
        create_resp = await client.post(
            f"/api/v1/projects/{test_project['id']}/tasks",
            json={"title": "Done task"},
            headers=auth_headers,
        )
        task_id = create_resp.json()["id"]
        await client.patch(
            f"/api/v1/projects/{test_project['id']}/tasks/{task_id}",
            json={"status": "done"},
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/v1/projects/{test_project['id']}/tasks?status=done",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        for task in resp.json():
            assert task["status"] == "done"

    async def test_update_task(self, client: AsyncClient, auth_headers, test_project):
        create_resp = await client.post(
            f"/api/v1/projects/{test_project['id']}/tasks",
            json={"title": "Original"},
            headers=auth_headers,
        )
        task_id = create_resp.json()["id"]

        update_resp = await client.patch(
            f"/api/v1/projects/{test_project['id']}/tasks/{task_id}",
            json={"title": "Updated", "status": "in_progress"},
            headers=auth_headers,
        )
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["title"] == "Updated"
        assert data["status"] == "in_progress"

    async def test_delete_task(self, client: AsyncClient, auth_headers, test_project):
        create_resp = await client.post(
            f"/api/v1/projects/{test_project['id']}/tasks",
            json={"title": "To be deleted"},
            headers=auth_headers,
        )
        task_id = create_resp.json()["id"]

        del_resp = await client.delete(
            f"/api/v1/projects/{test_project['id']}/tasks/{task_id}",
            headers=auth_headers,
        )
        assert del_resp.status_code == 204

    async def test_viewer_cannot_create_task(self, client: AsyncClient, auth_headers, test_project):
        # Register a viewer user and invite them
        viewer_resp = await client.post("/api/v1/auth/register", json={
            "email": "viewer@example.com",
            "username": "vieweruser",
            "password": "password123",
        })
        viewer_token = viewer_resp.json()["access_token"]

        # Invite as viewer
        await client.post(
            f"/api/v1/projects/{test_project['id']}/members",
            json={"email": "viewer@example.com", "role": "viewer"},
            headers=auth_headers,
        )

        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
        resp = await client.post(
            f"/api/v1/projects/{test_project['id']}/tasks",
            json={"title": "Viewer trying to create"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403
