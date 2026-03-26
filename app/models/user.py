import uuid

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    telegram_link_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    owned_projects: Mapped[list["Project"]] = relationship(  # noqa: F821
        "Project", back_populates="owner", cascade="all, delete-orphan"
    )
    project_memberships: Mapped[list["ProjectMember"]] = relationship(  # noqa: F821
        "ProjectMember", back_populates="user", cascade="all, delete-orphan"
    )
    created_tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task", foreign_keys="Task.creator_id", back_populates="creator"
    )
    assigned_tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task", foreign_keys="Task.assignee_id", back_populates="assignee"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
