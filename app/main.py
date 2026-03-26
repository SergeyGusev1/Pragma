from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.redis_client import close_redis_pool, get_redis_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify connections
    await get_redis_pool()
    yield
    # Shutdown: clean up
    await close_redis_pool()


app = FastAPI(
    title="Task Manager API",
    description="A comprehensive task management API with projects, tasks, and Telegram notifications.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["System"])
async def health_check() -> dict:
    return {"status": "ok", "environment": settings.app_env}
