from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_auth_service, get_current_user, get_user_repo, require_admin
from app.api.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.application.auth_service import AuthService
from app.domain.models import UserPublic
from app.infrastructure.user_repository import UserRepository
from shared.enums import Role

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    try:
        _, token = await auth.register_resident(
            email=str(body.email),
            password=body.password,
            full_name=body.full_name,
        )
    except ValueError as e:
        if str(e) == "email_in_use":
            raise HTTPException(status.HTTP_409_CONFLICT, "Request failed")
        raise
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    try:
        _, token = await auth.login(str(body.email), body.password)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Request failed")
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(user: Annotated[UserPublic, Depends(get_current_user)]) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )


@router.get("/maintenance-staff", response_model=list[UserResponse])
async def list_maintenance_staff(
    _: Annotated[UserPublic, Depends(require_admin)],
    repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> list[UserResponse]:
    users = await repo.list_by_role(Role.MAINTENANCE_STAFF)
    return [
        UserResponse(
            id=u.id or "",
            email=u.email,
            full_name=u.full_name,
            role=u.role,
        )
        for u in users
        if u.id
    ]
