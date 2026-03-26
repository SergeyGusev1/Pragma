import secrets
import uuid

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.core.dependencies import get_current_user_from_token
from app.core.exceptions import ConflictError
from app.core.redis_client import get_redis
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import TelegramLinkResponse, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user_from_token)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user_from_token),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    repo = UserRepository(session)

    if body.username and body.username != current_user.username:
        existing = await repo.get_by_username(body.username)
        if existing:
            raise ConflictError("Username already taken")

    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        return current_user

    return await repo.update(current_user, **update_data)


@router.delete("/me", status_code=204)
async def deactivate_me(
    current_user: User = Depends(get_current_user_from_token),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    repo = UserRepository(session)
    await repo.update(current_user, is_active=False)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    _: User = Depends(get_current_user_from_token),
) -> User:
    from app.core.exceptions import NotFoundError

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise NotFoundError("User not found")
    return user


@router.post("/me/telegram-link", response_model=TelegramLinkResponse)
async def generate_telegram_link_token(
    current_user: User = Depends(get_current_user_from_token),
    session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
) -> TelegramLinkResponse:
    """Generate a short-lived token so user can link their Telegram account."""
    token = secrets.token_urlsafe(32)
    repo = UserRepository(session)
    await repo.update(current_user, telegram_link_token=token)

    # Also store in Redis for quick lookup by the bot (5 min TTL)
    await redis.setex(f"tg_link:{token}", 300, str(current_user.id))

    return TelegramLinkResponse(link_token=token)
