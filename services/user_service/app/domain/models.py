from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from shared.enums import Role


class UserDocument(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str | None = None
    email: EmailStr
    password_hash: str
    full_name: str
    role: Role
    created_at: datetime

    def to_mongo(self) -> dict[str, Any]:
        doc: dict[str, Any] = {
            "email": self.email,
            "password_hash": self.password_hash,
            "full_name": self.full_name,
            "role": self.role.value,
            "created_at": self.created_at,
        }
        if self.id:
            doc["_id"] = ObjectId(self.id)
        return doc

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "UserDocument":
        oid = doc.get("_id")
        return cls(
            id=str(oid) if oid else None,
            email=doc["email"],
            password_hash=doc["password_hash"],
            full_name=doc["full_name"],
            role=Role(doc["role"]),
            created_at=doc["created_at"],
        )


class UserPublic(BaseModel):
    id: str = Field(pattern=r"^[a-f0-9]{24}$")
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    role: Role

    @field_validator("id")
    @classmethod
    def objectid_shape(cls, v: str) -> str:
        if len(v) != 24:
            raise ValueError("invalid user id")
        return v
