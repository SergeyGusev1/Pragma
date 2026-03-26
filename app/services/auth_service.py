import uuid
from datetime import UTC, datetime

from jose import JWTError
from redis.asyncio import Redis

from app.core.config import settings
from app.core.exceptions import BadRequestError, ConflictError, UnauthorizedError
from app.core.redis_client import blacklist_token, is_token_blacklisted
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenPair


class AuthService:
    def __init__(self, user_repo: UserRepository, redis: Redis) -> None:
        self.user_repo = user_repo
        self.redis = redis

    async def register(self, email: str, username: str, password: str) -> User:
        if await self.user_repo.get_by_email(email):
            raise ConflictError("Email already registered")
        if await self.user_repo.get_by_username(username):
            raise ConflictError("Username already taken")

        return await self.user_repo.create(
            email=email,
            username=username,
            hashed_password=hash_password(password),
        )

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is deactivated")
        return user

    def _build_token_pair(self, user_id: uuid.UUID) -> TokenPair:
        access_token, _ = create_access_token(str(user_id))
        refresh_token, _ = create_refresh_token(str(user_id))
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self.authenticate(email, password)
        return self._build_token_pair(user.id)

    async def register_and_login(
        self, email: str, username: str, password: str
    ) -> TokenPair:
        user = await self.register(email, username, password)
        return self._build_token_pair(user.id)

    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = decode_token(refresh_token)
        except JWTError as exc:
            raise UnauthorizedError("Invalid refresh token") from exc

        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type")

        jti = payload.get("jti")
        if jti and await is_token_blacklisted(self.redis, jti):
            raise UnauthorizedError("Token has been revoked")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedError("Invalid token payload")

        user = await self.user_repo.get_by_id(uuid.UUID(user_id))
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or deactivated")

        # Blacklist the old refresh token
        if jti:
            exp = payload.get("exp", 0)
            ttl = max(0, int(exp - datetime.now(UTC).timestamp()))
            await blacklist_token(self.redis, jti, ttl)

        return self._build_token_pair(user.id)

    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token)
        except JWTError as exc:
            raise BadRequestError("Invalid token") from exc

        jti = payload.get("jti")
        if jti:
            exp = payload.get("exp", 0)
            ttl = max(1, int(exp - datetime.now(UTC).timestamp()))
            await blacklist_token(self.redis, jti, ttl)
