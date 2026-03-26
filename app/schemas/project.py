import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.project import ProjectRole


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class ProjectMemberRead(BaseModel):
    user_id: uuid.UUID
    username: str
    email: str
    role: ProjectRole
    joined_at: datetime

    model_config = {"from_attributes": True}


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectDetailRead(ProjectRead):
    members: list[ProjectMemberRead] = []


class MemberInviteRequest(BaseModel):
    email: EmailStr
    role: ProjectRole = ProjectRole.viewer


class MemberRoleUpdateRequest(BaseModel):
    role: ProjectRole
