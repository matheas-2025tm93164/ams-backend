from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.complaint_service import ComplaintApplicationService
from app.config import get_settings
from app.domain.models import JwtUser
from app.infrastructure.complaint_repository import ComplaintRepository
from app.infrastructure.mongo import MongoConnection
from app.infrastructure.user_client import UserServiceClient
from shared.jwt_tokens import verify_bearer_token

security = HTTPBearer()


def get_mongo() -> MongoConnection:
    raise RuntimeError("override")


def get_user_client() -> UserServiceClient:
    return UserServiceClient()


def get_complaint_repo(mongo: Annotated[MongoConnection, Depends(get_mongo)]) -> ComplaintRepository:
    return ComplaintRepository(mongo.db)


def get_complaint_service(
    repo: Annotated[ComplaintRepository, Depends(get_complaint_repo)],
    users: Annotated[UserServiceClient, Depends(get_user_client)],
) -> ComplaintApplicationService:
    return ComplaintApplicationService(repo, users)


async def get_jwt_user(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> JwtUser:
    settings = get_settings()
    try:
        payload = verify_bearer_token(
            creds.credentials,
            settings.jwt_secret,
            settings.jwt_algorithm,
        )
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Request failed")
    sub = payload.get("sub")
    email = payload.get("email")
    role = payload.get("role")
    if not isinstance(sub, str) or not isinstance(email, str) or not isinstance(role, str):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Request failed")
    return JwtUser(id=sub, email=email, role=role)
