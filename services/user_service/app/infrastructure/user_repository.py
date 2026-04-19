from __future__ import annotations

from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.models import UserDocument
from shared.enums import Role


class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["users"]

    async def ensure_indexes(self) -> None:
        await self._col.create_index("email", unique=True)

    async def create(self, user: UserDocument) -> UserDocument:
        doc = user.to_mongo()
        doc.pop("_id", None)
        result = await self._col.insert_one(doc)
        user.id = str(result.inserted_id)
        return user

    async def find_by_email(self, email: str) -> UserDocument | None:
        doc = await self._col.find_one({"email": email})
        if not doc:
            return None
        return UserDocument.from_mongo(doc)

    async def find_by_id(self, user_id: str) -> UserDocument | None:
        from bson import ObjectId
        from bson.errors import InvalidId

        try:
            oid = ObjectId(user_id)
        except InvalidId:
            return None
        doc = await self._col.find_one({"_id": oid})
        if not doc:
            return None
        return UserDocument.from_mongo(doc)

    async def list_maintenance_staff_ids(self) -> list[str]:
        cursor = self._col.find({"role": "maintenance_staff"}, {"_id": 1})
        return [str(d["_id"]) async for d in cursor]

    async def list_by_role(self, role: Role) -> list[UserDocument]:
        cursor = self._col.find({"role": role.value})
        return [UserDocument.from_mongo(d) async for d in cursor]

    @staticmethod
    def utcnow() -> datetime:
        return datetime.now(timezone.utc)
