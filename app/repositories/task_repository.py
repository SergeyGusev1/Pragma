import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Tag, Task, TaskPriority, TaskStatus
from app.repositories.base_repository import BaseRepository


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Task, session)

    async def get_with_tags(self, task_id: uuid.UUID) -> Task | None:
        stmt = (
            select(Task)
            .where(Task.id == task_id)
            .options(selectinload(Task.tags))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_with_filters(
        self,
        project_id: uuid.UUID,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: uuid.UUID | None = None,
        deadline_before: datetime | None = None,
        deadline_after: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Task]:
        stmt = (
            select(Task)
            .where(Task.project_id == project_id)
            .options(selectinload(Task.tags))
            .order_by(Task.created_at.desc())
        )

        if status is not None:
            stmt = stmt.where(Task.status == status)
        if priority is not None:
            stmt = stmt.where(Task.priority == priority)
        if assignee_id is not None:
            stmt = stmt.where(Task.assignee_id == assignee_id)
        if deadline_before is not None:
            stmt = stmt.where(Task.deadline <= deadline_before)
        if deadline_after is not None:
            stmt = stmt.where(Task.deadline >= deadline_after)

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_tasks_due_for_reminder(
        self, from_dt: datetime, to_dt: datetime
    ) -> list[Task]:
        """Return tasks with deadline in [from_dt, to_dt] where reminder not yet sent."""
        stmt = (
            select(Task)
            .where(
                Task.deadline >= from_dt,
                Task.deadline <= to_dt,
                Task.reminder_sent.is_(False),
                Task.status != TaskStatus.done,
            )
            .options(selectinload(Task.assignee))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class TagRepository(BaseRepository[Tag]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Tag, session)

    async def get_by_name(self, name: str) -> Tag | None:
        return await self.get_by_field("name", name)
