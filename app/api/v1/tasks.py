import uuid

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.core.dependencies import get_current_user_from_token
from app.core.redis_client import get_redis
from app.models.task import TaskPriority, TaskStatus
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TagRepository, TaskRepository
from app.schemas.task import TagCreate, TagRead, TaskCreate, TaskRead, TaskUpdate
from app.services.task_service import TaskService
from datetime import datetime

router = APIRouter(tags=["Tasks"])


def _get_task_service(
    session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
) -> TaskService:
    return TaskService(
        TaskRepository(session),
        TagRepository(session),
        ProjectRepository(session),
        redis,
    )


@router.post("/projects/{project_id}/tasks", response_model=TaskRead, status_code=201)
async def create_task(
    project_id: uuid.UUID,
    body: TaskCreate,
    current_user: User = Depends(get_current_user_from_token),
    service: TaskService = Depends(_get_task_service),
) -> TaskRead:
    task = await service.create_task(
        project_id=project_id,
        creator_id=current_user.id,
        title=body.title,
        description=body.description,
        status=body.status,
        priority=body.priority,
        deadline=body.deadline,
        assignee_id=body.assignee_id,
    )
    return TaskRead.model_validate(task)


@router.get("/projects/{project_id}/tasks", response_model=list[TaskRead])
async def list_tasks(
    project_id: uuid.UUID,
    status: TaskStatus | None = Query(default=None),
    priority: TaskPriority | None = Query(default=None),
    assignee_id: uuid.UUID | None = Query(default=None),
    deadline_before: datetime | None = Query(default=None),
    deadline_after: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user_from_token),
    service: TaskService = Depends(_get_task_service),
) -> list[TaskRead]:
    tasks = await service.list_tasks(
        project_id=project_id,
        user_id=current_user.id,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        deadline_before=deadline_before,
        deadline_after=deadline_after,
        page=page,
        size=size,
    )
    return [TaskRead.model_validate(t) for t in tasks]


@router.get("/projects/{project_id}/tasks/{task_id}", response_model=TaskRead)
async def get_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user_from_token),
    service: TaskService = Depends(_get_task_service),
) -> TaskRead:
    task = await service.get_task_or_404(project_id, task_id, current_user.id)
    return TaskRead.model_validate(task)


@router.patch("/projects/{project_id}/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    body: TaskUpdate,
    current_user: User = Depends(get_current_user_from_token),
    service: TaskService = Depends(_get_task_service),
) -> TaskRead:
    task = await service.update_task(
        project_id=project_id,
        task_id=task_id,
        user_id=current_user.id,
        **body.model_dump(exclude_none=True),
    )
    return TaskRead.model_validate(task)


@router.delete("/projects/{project_id}/tasks/{task_id}", status_code=204)
async def delete_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user_from_token),
    service: TaskService = Depends(_get_task_service),
) -> None:
    await service.delete_task(project_id, task_id, current_user.id)


@router.post("/projects/{project_id}/tasks/{task_id}/tags/{tag_id}", response_model=TaskRead)
async def add_tag_to_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    tag_id: uuid.UUID,
    current_user: User = Depends(get_current_user_from_token),
    service: TaskService = Depends(_get_task_service),
) -> TaskRead:
    task = await service.add_tag_to_task(project_id, task_id, current_user.id, tag_id)
    return TaskRead.model_validate(task)


@router.delete("/projects/{project_id}/tasks/{task_id}/tags/{tag_id}", response_model=TaskRead)
async def remove_tag_from_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    tag_id: uuid.UUID,
    current_user: User = Depends(get_current_user_from_token),
    service: TaskService = Depends(_get_task_service),
) -> TaskRead:
    task = await service.remove_tag_from_task(project_id, task_id, current_user.id, tag_id)
    return TaskRead.model_validate(task)


# --- Tags ---
tags_router = APIRouter(prefix="/tags", tags=["Tags"])


@tags_router.get("/", response_model=list[TagRead])
async def list_tags(
    _: User = Depends(get_current_user_from_token),
    session: AsyncSession = Depends(get_async_session),
) -> list[TagRead]:
    repo = TagRepository(session)
    tags = await repo.list_all()
    return [TagRead.model_validate(t) for t in tags]


@tags_router.post("/", response_model=TagRead, status_code=201)
async def create_tag(
    body: TagCreate,
    _: User = Depends(get_current_user_from_token),
    session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
) -> TagRead:
    service = TaskService(TaskRepository(session), TagRepository(session), ProjectRepository(session), redis)
    tag = await service.create_or_get_tag(body.name, body.color)
    return TagRead.model_validate(tag)
