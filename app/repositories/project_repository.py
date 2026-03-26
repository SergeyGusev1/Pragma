import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project, ProjectMember, ProjectRole
from app.repositories.base_repository import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Project, session)

    async def get_with_members(self, project_id: uuid.UUID) -> Project | None:
        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.members).selectinload(ProjectMember.user))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_projects_for_user(self, user_id: uuid.UUID) -> list[Project]:
        """Return all projects where the user is a member (including owner)."""
        stmt = (
            select(Project)
            .join(ProjectMember, Project.id == ProjectMember.project_id)
            .where(ProjectMember.user_id == user_id)
            .order_by(Project.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_member(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> ProjectMember | None:
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_member_role(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> ProjectRole | None:
        member = await self.get_member(project_id, user_id)
        return member.role if member else None

    async def add_member(
        self, project_id: uuid.UUID, user_id: uuid.UUID, role: ProjectRole
    ) -> ProjectMember:
        member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
        self.session.add(member)
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def update_member_role(
        self, member: ProjectMember, role: ProjectRole
    ) -> ProjectMember:
        member.role = role
        self.session.add(member)
        await self.session.flush()
        return member

    async def remove_member(self, member: ProjectMember) -> None:
        await self.session.delete(member)
        await self.session.flush()
