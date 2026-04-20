from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas_internal import UserIdBatchRequest
from app.api.deps import get_user_repo
from app.infrastructure.user_repository import UserRepository

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/users/{user_id}")
async def get_user_exists(
    user_id: str,
    repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> dict:
    user = await repo.find_by_id(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")
    return {
        "id": user.id,
        "role": user.role.value,
        "full_name": user.full_name,
        "email": user.email,
        "account_status": user.account_status.value,
    }


@router.post("/users/batch")
async def batch_users(
    body: UserIdBatchRequest,
    repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> list[dict]:
    seen: set[str] = set()
    unique: list[str] = []
    for i in body.ids:
        if i and i not in seen:
            seen.add(i)
            unique.append(i)
    users = await repo.find_by_ids(unique)
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": str(u.email),
            "role": u.role.value,
            "account_status": u.account_status.value,
        }
        for u in users
        if u.id
    ]
