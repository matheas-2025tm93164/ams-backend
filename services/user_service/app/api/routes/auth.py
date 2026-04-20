from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_auth_service, get_current_user, get_user_repo, require_admin
from app.api.routes import admin_users as admin_users_routes
from app.api.schemas import LoginRequest, TokenResponse, UserResponse
from app.application.auth_service import AuthService
from app.domain.models import UserPublic
from app.infrastructure.user_repository import UserRepository
from shared.enums import Role

router = APIRouter(prefix="/auth", tags=["auth"])
router.include_router(admin_users_routes.router, prefix="/admin")


def _user_response(u: UserPublic) -> UserResponse:
    return UserResponse(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        role=u.role,
        account_status=u.account_status,
    )


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
    return _user_response(user)


@router.get("/maintenance-staff", response_model=list[UserResponse])
async def list_maintenance_staff(
    _: Annotated[UserPublic, Depends(require_admin)],
    repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> list[UserResponse]:
    users = await repo.list_by_role(Role.MAINTENANCE_STAFF, only_active=True)
    return [_user_response(AuthService.to_public(u)) for u in users if u.id]
