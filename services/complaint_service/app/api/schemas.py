from __future__ import annotations

from datetime import datetime

import re

from pydantic import BaseModel, Field, field_validator

from shared.enums import Category, ComplaintStatus, Priority


class ComplaintCreate(BaseModel):
    category: Category
    priority: Priority
    description: str = Field(min_length=1, max_length=8000)


class ComplaintPatchBody(BaseModel):
    assigned_staff_id: str | None = Field(default=None)
    category: Category | None = None
    priority: Priority | None = None
    description: str | None = Field(default=None, min_length=1, max_length=8000)
    status: ComplaintStatus | None = None
    resident_feedback: str | None = Field(default=None, max_length=4000)
    rating: int | None = Field(default=None, ge=1, le=5)

    @field_validator("assigned_staff_id", mode="before")
    @classmethod
    def normalize_assignee(cls, v: object) -> object:
        if v == "":
            return None
        return v

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: object) -> object:
        if isinstance(v, str):
            s = v.strip()
            if s == "":
                return None
            return s
        return v

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, v: object) -> object:
        if v == "":
            return None
        return v

    @field_validator("resident_feedback", mode="before")
    @classmethod
    def normalize_feedback(cls, v: object) -> object:
        if v == "":
            return None
        return v

    @field_validator("rating", mode="before")
    @classmethod
    def normalize_rating(cls, v: object) -> object:
        if v == "" or v is None:
            return None
        return v

    @field_validator("assigned_staff_id")
    @classmethod
    def assignee_shape(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not re.match(r"^[a-f0-9]{24}$", v):
            raise ValueError("invalid assignee id")
        return v


class ComplaintResponse(BaseModel):
    id: str
    public_id: str
    resident_id: str
    resident_name: str | None = None
    category: Category
    priority: Priority
    description: str
    status: ComplaintStatus
    assigned_staff_id: str | None
    assigned_staff_name: str | None = None
    images: list[str]
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    resident_feedback: str | None
    rating: int | None


class AnalyticsResponse(BaseModel):
    by_category: list[dict]
