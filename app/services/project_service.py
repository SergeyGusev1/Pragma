import uuid

from redis.asyncio import Redis

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.redis_client import cache_delete, cache_get, cache_invalidate_pattern, cache_set
from app.models.project import Project, ProjectMember, ProjectRole
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository

_ROLE_RANK = {ProjectRole.viewer: 0, ProjectRole.editor: 1, ProjectRole.owner: 2}


def _check_role(actual: ProjectRole | None, required: ProjectRole) -> None:
    """Raise ForbiddenError if actual role doesn't meet minimum required."""
    if actual is None or _ROLE_RANK[actual] < _ROLE_RANK[required]:
        raise ForbiddenError("Insufficient project permissions")


class ProjectService:
    def __init__(
        self,
        project_repo: ProjectRepository,
        user_repo: UserRepository,
        redis: Redis,
    ) -> None:
        self.project_repo = project_repo
        self.user_repo = user_repo
        self.redis = redis

    async def create_project(
        self, owner_id: uuid.UUID, name: str, description: str | None
    ) -> Project:
        project = await self.project_repo.create(
            name=name, description=description, owner_id=owner_id
        )
        # Auto-add owner as member with role 'owner'
        await self.project_repo.add_member(project.id, owner_id, ProjectRole.owner)
        await cache_invalidate_pattern(self.redis, f"cache:projects:user:{owner_id}:*")
        return project

    async def get_project_or_404(self, project_id: uuid.UUID) -> Project:
        project = await self.project_repo.get_with_members(project_id)
        if not project:
            raise NotFoundError("Project not found")
        return project

    async def list_user_projects(self, user_id: uuid.UUID) -> list[Project]:
        cache_key = f"cache:projects:user:{user_id}:list"
        cached = await cache_get(self.redis, cache_key)
        if cached is not None:
            return cached  # Returns raw dict list; router will re-parse with Pydantic

        projects = await self.project_repo.get_projects_for_user(user_id)
        await cache_set(self.redis, cache_key, [str(p.id) for p in projects], ttl=60)
        return projects

    async def require_membership(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> ProjectRole:
        role = await self.project_repo.get_member_role(project_id, user_id)
        if role is None:
            raise ForbiddenError("You are not a member of this project")
        return role

    async def update_project(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str | None,
        description: str | None,
    ) -> Project:
        role = await self.require_membership(project_id, user_id)
        _check_role(role, ProjectRole.editor)

        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundError("Project not found")

        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description

        updated = await self.project_repo.update(project, **update_data)
        await cache_invalidate_pattern(self.redis, f"cache:projects:*")
        return updated

    async def delete_project(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        role = await self.require_membership(project_id, user_id)
        _check_role(role, ProjectRole.owner)

        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundError("Project not found")

        await self.project_repo.delete(project)
        await cache_invalidate_pattern(self.redis, "cache:projects:*")

    async def invite_member(
        self,
        project_id: uuid.UUID,
        inviter_id: uuid.UUID,
        invitee_email: str,
        role: ProjectRole,
    ) -> ProjectMember:
        inviter_role = await self.require_membership(project_id, inviter_id)
        _check_role(inviter_role, ProjectRole.owner)

        invitee = await self.user_repo.get_by_email(invitee_email)
        if not invitee:
            raise NotFoundError("User with this email not found")

        existing = await self.project_repo.get_member(project_id, invitee.id)
        if existing:
            raise ConflictError("User is already a member of this project")

        if role == ProjectRole.owner:
            raise ForbiddenError("Cannot assign owner role via invite")

        return await self.project_repo.add_member(project_id, invitee.id, role)

    async def update_member_role(
        self,
        project_id: uuid.UUID,
        requester_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role: ProjectRole,
    ) -> ProjectMember:
        requester_role = await self.require_membership(project_id, requester_id)
        _check_role(requester_role, ProjectRole.owner)

        if new_role == ProjectRole.owner:
            raise ForbiddenError("Cannot assign owner role")

        member = await self.project_repo.get_member(project_id, target_user_id)
        if not member:
            raise NotFoundError("Member not found in this project")

        if member.role == ProjectRole.owner:
            raise ForbiddenError("Cannot change the owner's role")

        return await self.project_repo.update_member_role(member, new_role)

    async def remove_member(
        self,
        project_id: uuid.UUID,
        requester_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> None:
        requester_role = await self.require_membership(project_id, requester_id)
        _check_role(requester_role, ProjectRole.owner)

        member = await self.project_repo.get_member(project_id, target_user_id)
        if not member:
            raise NotFoundError("Member not found in this project")

        if member.role == ProjectRole.owner:
            raise ForbiddenError("Cannot remove the project owner")

        await self.project_repo.remove_member(member)
        await cache_delete(self.redis, f"cache:projects:user:{target_user_id}:list")
