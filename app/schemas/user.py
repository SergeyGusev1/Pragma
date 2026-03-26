import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str
    is_active: bool
    telegram_chat_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")


class TelegramLinkResponse(BaseModel):
    link_token: str
    expires_in_seconds: int = 300
    instruction: str = "Send this token to the Telegram bot using /link <token>"
