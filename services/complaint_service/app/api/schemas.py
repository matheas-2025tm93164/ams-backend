from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from shared.enums import Category, ComplaintStatus, Priority


class ComplaintCreate(BaseModel):
    category: Category
    priority: Priority
    description: str = Field(min_length=1, max_length=8000)


class ComplaintPatchBody(BaseModel):
    assigned_staff_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{24}$")
    category: Category | None = None
    priority: Priority | None = None
    status: ComplaintStatus | None = None
    resident_feedback: str | None = Field(default=None, max_length=4000)
    rating: int | None = Field(default=None, ge=1, le=5)


class ComplaintResponse(BaseModel):
    id: str
    public_id: str
    resident_id: str
    category: Category
    priority: Priority
    description: str
    status: ComplaintStatus
    assigned_staff_id: str | None
    images: list[str]
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    resident_feedback: str | None
    rating: int | None


class AnalyticsResponse(BaseModel):
    by_category: list[dict]
