
import redis.asyncio as aioredis
from fastapi import Depends
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.core.exceptions import UnauthorizedError
from app.core.redis_client import get_redis, is_token_blacklisted
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user_repository import UserRepository


async def get_current_user(
    token: str = Depends(lambda: None),
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> User:
    # This is a placeholder — the actual token is extracted via HTTPBearer below
    raise UnauthorizedError()


# Real dependency used in routes
import uuid  # noqa: E402

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer  # noqa: E402

_bearer = HTTPBearer(auto_error=False)


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Missing authentication token")

    try:
        payload = decode_token(credentials.credentials)
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    jti = payload.get("jti")
    if jti and await is_token_blacklisted(redis, jti):
        raise UnauthorizedError("Token has been revoked")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token payload")

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(uuid.UUID(user_id))

    if not user or not user.is_active:
        raise UnauthorizedError("User not found or deactivated")

    return user


# Shorthand alias used in route signatures
CurrentUser = Depends(get_current_user_from_token)
