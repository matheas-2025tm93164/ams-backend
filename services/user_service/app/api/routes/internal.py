from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

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
    return {"id": user.id, "role": user.role.value}
