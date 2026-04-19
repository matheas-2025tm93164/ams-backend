from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator

from shared.enums import Category, ComplaintStatus, Priority


class ComplaintDocument(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str | None = None
    public_id: str = Field(pattern=r"^CMP-\d{4}-[A-F0-9]{6}$")
    resident_id: str
    category: Category
    priority: Priority
    description: str = Field(min_length=1, max_length=8000)
    status: ComplaintStatus
    assigned_staff_id: str | None = None
    images: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    resident_feedback: str | None = Field(default=None, max_length=4000)
    rating: int | None = Field(default=None, ge=1, le=5)

    def to_mongo(self) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "public_id": self.public_id,
            "resident_id": self.resident_id,
            "category": self.category.value,
            "priority": self.priority.value,
            "description": self.description,
            "status": self.status.value,
            "assigned_staff_id": self.assigned_staff_id,
            "images": self.images,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "resident_feedback": self.resident_feedback,
            "rating": self.rating,
        }
        if self.id:
            doc["_id"] = ObjectId(self.id)
        return doc

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "ComplaintDocument":
        oid = doc.get("_id")
        return cls(
            id=str(oid) if oid else None,
            public_id=doc["public_id"],
            resident_id=doc["resident_id"],
            category=Category(doc["category"]),
            priority=Priority(doc["priority"]),
            description=doc["description"],
            status=ComplaintStatus(doc["status"]),
            assigned_staff_id=doc.get("assigned_staff_id"),
            images=list(doc.get("images") or []),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
            completed_at=doc.get("completed_at"),
            resident_feedback=doc.get("resident_feedback"),
            rating=doc.get("rating"),
        )


class JwtUser(BaseModel):
    id: str
    email: str
    role: str
