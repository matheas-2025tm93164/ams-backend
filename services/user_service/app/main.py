from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import deps
from app.api.routes import auth
from app.api.routes import internal as internal_routes
from app.config import get_settings
from app.infrastructure.mongo import MongoConnection
from app.infrastructure.user_repository import UserRepository
from app.seed import seed_demo_users

_settings = get_settings()
_mongo: MongoConnection | None = None


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global _mongo
    _mongo = MongoConnection(_settings.mongo_uri, _settings.mongo_db)
    repo = UserRepository(_mongo.db)
    await repo.ensure_indexes()
    await seed_demo_users(repo)
    yield
    if _mongo:
        _mongo.close()
    _mongo = None


def get_mongo_singleton() -> MongoConnection:
    if _mongo is None:
        raise RuntimeError("Mongo not initialized")
    return _mongo


app = FastAPI(title="User Service", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(internal_routes.router)

app.dependency_overrides[deps.get_mongo] = get_mongo_singleton
