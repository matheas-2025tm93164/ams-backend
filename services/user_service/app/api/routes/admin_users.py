from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_auth_service, get_user_repo, require_admin
from app.api.schemas import AdminUserRow, ResidentOnboardRequest, StaffOnboardRequest, UserResponse
from app.application.auth_service import AuthService
from app.domain.models import UserDocument, UserPublic
from app.infrastructure.user_repository import UserRepository
from shared.enums import Role

router = APIRouter(tags=["admin"])


def _mask_aadhar(raw: str | None) -> str | None:
    if not raw or len(raw) < 4:
        return None
    return f"……{raw[-4:]}"


def _to_admin_row(u: UserDocument) -> AdminUserRow:
    assert u.id
    return AdminUserRow(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        role=u.role,
        account_status=u.account_status,
        phone=u.phone,
        address=u.address,
        aadhar_masked=_mask_aadhar(u.aadhar),
        family_members=list(u.family_members or []),
    )


def _user_response(u: UserPublic) -> UserResponse:
    return UserResponse(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        role=u.role,
        account_status=u.account_status,
    )


@router.get("/staff", response_model=list[AdminUserRow])
async def list_staff(
    _: Annotated[UserPublic, Depends(require_admin)],
    repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> list[AdminUserRow]:
    users = await repo.list_by_role(Role.MAINTENANCE_STAFF, only_active=False)
    return [_to_admin_row(u) for u in users if u.id]


@router.get("/residents", response_model=list[AdminUserRow])
async def list_residents(
    _: Annotated[UserPublic, Depends(require_admin)],
    repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> list[AdminUserRow]:
    users = await repo.list_by_role(Role.RESIDENT, only_active=False)
    return [_to_admin_row(u) for u in users if u.id]


@router.post("/staff/onboard", response_model=UserResponse)
async def onboard_staff(
    body: StaffOnboardRequest,
    _: Annotated[UserPublic, Depends(require_admin)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    try:
        u = await auth.onboard_staff(
            email=str(body.email),
            password=body.password,
            full_name=body.full_name,
            address=body.address,
            phone=body.phone,
            aadhar=body.aadhar,
        )
    except ValueError as e:
        if str(e) == "email_in_use":
            raise HTTPException(status.HTTP_409_CONFLICT, "Request failed")
        raise
    return _user_response(u)


@router.post("/residents/onboard", response_model=UserResponse)
async def onboard_resident(
    body: ResidentOnboardRequest,
    _: Annotated[UserPublic, Depends(require_admin)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    try:
        u = await auth.onboard_resident(
            email=str(body.email),
            password=body.password,
            full_name=body.full_name,
            phone=body.phone,
            aadhar=body.aadhar,
            family_members=body.family_members,
        )
    except ValueError as e:
        if str(e) == "email_in_use":
            raise HTTPException(status.HTTP_409_CONFLICT, "Request failed")
        if str(e) == "family_duplicate_primary":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Request failed")
        raise
    return _user_response(u)


@router.post("/users/{user_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: str,
    _: Annotated[UserPublic, Depends(require_admin)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    try:
        await auth.deactivate_user(user_id)
    except ValueError as e:
        if str(e) == "not_found":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Request failed")
        if str(e) == "cannot_deactivate_admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Request failed")
        raise
