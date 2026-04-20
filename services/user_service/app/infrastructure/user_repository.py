from __future__ import annotations

from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.models import UserDocument
from shared.enums import AccountStatus, Role


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

    async def find_by_ids(self, user_ids: list[str]) -> list[UserDocument]:
        from bson import ObjectId
        from bson.errors import InvalidId

        oids: list[ObjectId] = []
        for uid in user_ids:
            try:
                oids.append(ObjectId(uid))
            except (InvalidId, TypeError):
                continue
        if not oids:
            return []
        cursor = self._col.find({"_id": {"$in": oids}})
        return [UserDocument.from_mongo(d) async for d in cursor]

    async def list_maintenance_staff_ids(self) -> list[str]:
        cursor = self._col.find(self._active_staff_query(), {"_id": 1})
        return [str(d["_id"]) async for d in cursor]

    @staticmethod
    def _active_account_clause() -> dict:
        return {
            "$or": [
                {"account_status": AccountStatus.ACTIVE.value},
                {"account_status": {"$exists": False}},
            ]
        }

    def _active_staff_query(self) -> dict:
        return {
            "role": Role.MAINTENANCE_STAFF.value,
            **self._active_account_clause(),
        }

    async def list_by_role(self, role: Role, *, only_active: bool = False) -> list[UserDocument]:
        q: dict = {"role": role.value}
        if only_active:
            q = {"$and": [{"role": role.value}, self._active_account_clause()]}
        cursor = self._col.find(q)
        return [UserDocument.from_mongo(d) async for d in cursor]

    async def set_account_status(self, user_id: str, status: AccountStatus) -> bool:
        from bson import ObjectId
        from bson.errors import InvalidId

        try:
            oid = ObjectId(user_id)
        except InvalidId:
            return False
        r = await self._col.update_one(
            {"_id": oid},
            {"$set": {"account_status": status.value}},
        )
        return r.matched_count > 0

    @staticmethod
    def utcnow() -> datetime:
        return datetime.now(timezone.utc)
