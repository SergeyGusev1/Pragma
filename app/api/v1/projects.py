import uuid

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.core.dependencies import get_current_user_from_token
from app.core.redis_client import get_redis
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.schemas.project import (
    MemberInviteRequest,
    MemberRoleUpdateRequest,
    ProjectCreate,
    ProjectDetailRead,
    ProjectMemberRead,
    ProjectRead,
    ProjectUpdate,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


def _get_project_service(
    session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
) -> ProjectService:
    return ProjectService(
        ProjectRepository(session),
        UserRepository(session),
        redis,
    )


@router.post("/", response_model=ProjectRead, status_code=201)
async def create_project(
    body: ProjectCreate,
    current_user: User = Depends(get_current_user_from_token),
    service: ProjectService = Depends(_get_project_service),
) -> ProjectRead:
    project = await service.create_project(current_user.id, body.name, body.description)
    return ProjectRead.model_validate(project)


@router.get("/", response_model=list[ProjectRead])
async def list_projects(
    current_user: User = Depends(get_current_user_from_token),
    service: ProjectService = Depends(_get_project_service),
) -> list[ProjectRead]:
    projects = await service.list_user_projects(current_user.id)
    return [ProjectRead.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectDetailRead)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user_from_token),
    service: ProjectService = Depends(_get_project_service),
) -> ProjectDetailRead:
    await service.require_membership(project_id, current_user.id)
    project = await service.get_project_or_404(project_id)
    members = [
        ProjectMemberRead(
            user_id=m.user_id,
            username=m.user.username,
            email=m.user.email,
            role=m.role,
            joined_at=m.joined_at,
        )
        for m in project.members
    ]
    result = ProjectDetailRead.model_validate(project)
    result.members = members
    return result


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    current_user: User = Depends(get_current_user_from_token),
    service: ProjectService = Depends(_get_project_service),
) -> ProjectRead:
    project = await service.update_project(
        project_id, current_user.id, body.name, body.description
    )
    return ProjectRead.model_validate(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user_from_token),
    service: ProjectService = Depends(_get_project_service),
) -> None:
    await service.delete_project(project_id, current_user.id)


@router.post("/{project_id}/members", response_model=ProjectMemberRead, status_code=201)
async def invite_member(
    project_id: uuid.UUID,
    body: MemberInviteRequest,
    current_user: User = Depends(get_current_user_from_token),
    service: ProjectService = Depends(_get_project_service),
) -> ProjectMemberRead:
    member = await service.invite_member(project_id, current_user.id, body.email, body.role)
    user = await service.user_repo.get_by_id(member.user_id)
    return ProjectMemberRead(
        user_id=member.user_id,
        username=user.username,  # type: ignore[union-attr]
        email=user.email,  # type: ignore[union-attr]
        role=member.role,
        joined_at=member.joined_at,
    )


@router.get("/{project_id}/members", response_model=list[ProjectMemberRead])
async def list_members(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user_from_token),
    service: ProjectService = Depends(_get_project_service),
) -> list[ProjectMemberRead]:
    await service.require_membership(project_id, current_user.id)
    project = await service.get_project_or_404(project_id)
    return [
        ProjectMemberRead(
            user_id=m.user_id,
            username=m.user.username,
            email=m.user.email,
            role=m.role,
            joined_at=m.joined_at,
        )
        for m in project.members
    ]


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberRead)
async def update_member_role(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    body: MemberRoleUpdateRequest,
    current_user: User = Depends(get_current_user_from_token),
    service: ProjectService = Depends(_get_project_service),
) -> ProjectMemberRead:
    member = await service.update_member_role(project_id, current_user.id, user_id, body.role)
    user = await service.user_repo.get_by_id(user_id)
    return ProjectMemberRead(
        user_id=user_id,
        username=user.username,  # type: ignore[union-attr]
        email=user.email,  # type: ignore[union-attr]
        role=member.role,
        joined_at=member.joined_at,
    )


@router.delete("/{project_id}/members/{user_id}", status_code=204)
async def remove_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user_from_token),
    service: ProjectService = Depends(_get_project_service),
) -> None:
    await service.remove_member(project_id, current_user.id, user_id)
