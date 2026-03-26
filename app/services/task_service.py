import uuid
from datetime import datetime

from redis.asyncio import Redis

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.redis_client import cache_invalidate_pattern
from app.models.project import ProjectRole
from app.models.task import Tag, Task, TaskPriority, TaskStatus
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TagRepository, TaskRepository

_ROLE_RANK = {ProjectRole.viewer: 0, ProjectRole.editor: 1, ProjectRole.owner: 2}


class TaskService:
    def __init__(
        self,
        task_repo: TaskRepository,
        tag_repo: TagRepository,
        project_repo: ProjectRepository,
        redis: Redis,
    ) -> None:
        self.task_repo = task_repo
        self.tag_repo = tag_repo
        self.project_repo = project_repo
        self.redis = redis

    async def _require_project_role(
        self, project_id: uuid.UUID, user_id: uuid.UUID, min_role: ProjectRole
    ) -> ProjectRole:
        role = await self.project_repo.get_member_role(project_id, user_id)
        if role is None:
            raise ForbiddenError("Not a project member")
        if _ROLE_RANK[role] < _ROLE_RANK[min_role]:
            raise ForbiddenError("Insufficient permissions")
        return role

    async def create_task(
        self,
        project_id: uuid.UUID,
        creator_id: uuid.UUID,
        title: str,
        description: str | None,
        status: TaskStatus,
        priority: TaskPriority,
        deadline: datetime | None,
        assignee_id: uuid.UUID | None,
    ) -> Task:
        await self._require_project_role(project_id, creator_id, ProjectRole.editor)

        # Validate assignee is a project member
        if assignee_id is not None:
            member_role = await self.project_repo.get_member_role(
                project_id, assignee_id
            )
            if member_role is None:
                raise ForbiddenError("Assignee is not a member of this project")

        task = await self.task_repo.create(
            title=title,
            description=description,
            status=status,
            priority=priority,
            deadline=deadline,
            project_id=project_id,
            creator_id=creator_id,
            assignee_id=assignee_id,
        )
        await cache_invalidate_pattern(
            self.redis, f"cache:tasks:project:{project_id}:*"
        )
        return await self.task_repo.get_with_tags(task.id)  # type: ignore[return-value]

    async def get_task_or_404(
        self, project_id: uuid.UUID, task_id: uuid.UUID, user_id: uuid.UUID
    ) -> Task:
        await self._require_project_role(project_id, user_id, ProjectRole.viewer)
        task = await self.task_repo.get_with_tags(task_id)
        if not task or task.project_id != project_id:
            raise NotFoundError("Task not found")
        return task

    async def list_tasks(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: uuid.UUID | None,
        deadline_before: datetime | None,
        deadline_after: datetime | None,
        page: int,
        size: int,
    ) -> list[Task]:
        await self._require_project_role(project_id, user_id, ProjectRole.viewer)
        offset = (page - 1) * size
        return await self.task_repo.list_with_filters(
            project_id=project_id,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            deadline_before=deadline_before,
            deadline_after=deadline_after,
            offset=offset,
            limit=size,
        )

    async def update_task(
        self,
        project_id: uuid.UUID,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        **update_data,
    ) -> Task:
        task = await self.task_repo.get_with_tags(task_id)
        if not task or task.project_id != project_id:
            raise NotFoundError("Task not found")

        role = await self.project_repo.get_member_role(project_id, user_id)
        if role is None:
            raise ForbiddenError("Not a project member")

        # Editors+ or the assignee can update
        is_editor = _ROLE_RANK.get(role, -1) >= _ROLE_RANK[ProjectRole.editor]
        is_assignee = task.assignee_id == user_id
        if not is_editor and not is_assignee:
            raise ForbiddenError("Insufficient permissions to update this task")

        # Validate new assignee if changing
        new_assignee_id = update_data.get("assignee_id")
        if new_assignee_id is not None:
            member_role = await self.project_repo.get_member_role(
                project_id, new_assignee_id
            )
            if member_role is None:
                raise ForbiddenError("Assignee must be a project member")

        # Reset reminder_sent if deadline changes
        if "deadline" in update_data and update_data["deadline"] != task.deadline:
            update_data["reminder_sent"] = False

        filtered = {k: v for k, v in update_data.items() if v is not None}
        updated = await self.task_repo.update(task, **filtered)
        await cache_invalidate_pattern(
            self.redis, f"cache:tasks:project:{project_id}:*"
        )
        return updated

    async def delete_task(
        self, project_id: uuid.UUID, task_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        await self._require_project_role(project_id, user_id, ProjectRole.editor)
        task = await self.task_repo.get_by_id(task_id)
        if not task or task.project_id != project_id:
            raise NotFoundError("Task not found")
        await self.task_repo.delete(task)
        await cache_invalidate_pattern(
            self.redis, f"cache:tasks:project:{project_id}:*"
        )

    async def add_tag_to_task(
        self,
        project_id: uuid.UUID,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        tag_id: uuid.UUID,
    ) -> Task:
        await self._require_project_role(project_id, user_id, ProjectRole.editor)
        task = await self.task_repo.get_with_tags(task_id)
        if not task or task.project_id != project_id:
            raise NotFoundError("Task not found")

        tag = await self.tag_repo.get_by_id(tag_id)
        if not tag:
            raise NotFoundError("Tag not found")

        if tag not in task.tags:
            task.tags.append(tag)
            await self.task_repo.session.flush()

        return task

    async def remove_tag_from_task(
        self,
        project_id: uuid.UUID,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        tag_id: uuid.UUID,
    ) -> Task:
        await self._require_project_role(project_id, user_id, ProjectRole.editor)
        task = await self.task_repo.get_with_tags(task_id)
        if not task or task.project_id != project_id:
            raise NotFoundError("Task not found")

        task.tags = [t for t in task.tags if t.id != tag_id]
        await self.task_repo.session.flush()
        return task

    async def create_or_get_tag(self, name: str, color: str) -> Tag:
        existing = await self.tag_repo.get_by_name(name)
        if existing:
            return existing
        return await self.tag_repo.create(name=name, color=color)
