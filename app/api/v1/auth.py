from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_async_session
from app.core.redis_client import get_redis
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


def _get_auth_service(
    session: AsyncSession = Depends(get_async_session),
    redis: Redis = Depends(get_redis),
) -> AuthService:
    return AuthService(UserRepository(session), redis)


@router.post("/register", response_model=TokenPair, status_code=201)
async def register(
    body: RegisterRequest,
    service: AuthService = Depends(_get_auth_service),
) -> TokenPair:
    return await service.register_and_login(body.email, body.username, body.password)


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest,
    service: AuthService = Depends(_get_auth_service),
) -> TokenPair:
    return await service.login(body.email, body.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    service: AuthService = Depends(_get_auth_service),
) -> TokenPair:
    return await service.refresh(body.refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    body: LogoutRequest,
    service: AuthService = Depends(_get_auth_service),
) -> None:
    await service.logout(body.refresh_token)
