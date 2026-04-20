from __future__ import annotations

from pydantic import BaseModel, Field


class UserIdBatchRequest(BaseModel):
    ids: list[str] = Field(default_factory=list, max_length=200)
