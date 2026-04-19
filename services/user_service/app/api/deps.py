from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.auth_service import AuthService
from app.config import get_settings
from app.domain.models import UserPublic
from app.infrastructure.mongo import MongoConnection
from app.infrastructure.user_repository import UserRepository
from shared.enums import Role
from shared.jwt_tokens import verify_bearer_token

security = HTTPBearer(auto_error=False)


def get_mongo() -> MongoConnection:
    raise RuntimeError("override in main")


def get_user_repo(
    mongo: Annotated[MongoConnection, Depends(get_mongo)],
) -> UserRepository:
    return UserRepository(mongo.db)


def get_auth_service(
    repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> AuthService:
    return AuthService(repo)


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> UserPublic:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    settings = get_settings()
    try:
        payload = verify_bearer_token(
            creds.credentials,
            settings.jwt_secret,
            settings.jwt_algorithm,
        )
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    user = await auth.get_user(sub)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


async def require_admin(user: Annotated[UserPublic, Depends(get_current_user)]) -> UserPublic:
    if user.role != Role.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Request failed")
    return user
