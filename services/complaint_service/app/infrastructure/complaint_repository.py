from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.models import ComplaintDocument
from shared.enums import Category, ComplaintStatus, Priority


class ComplaintFilter:
    def __init__(
        self,
        status: ComplaintStatus | None = None,
        category: Category | None = None,
        priority: Priority | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> None:
        self.status = status
        self.category = category
        self.priority = priority
        self.date_from = date_from
        self.date_to = date_to


class ComplaintRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["complaints"]

    async def ensure_indexes(self) -> None:
        await self._col.create_index("public_id", unique=True)
        await self._col.create_index([("status", 1), ("created_at", -1)])
        await self._col.create_index([("resident_id", 1), ("created_at", -1)])
        await self._col.create_index([("assigned_staff_id", 1), ("status", 1)])

    async def create(self, c: ComplaintDocument) -> ComplaintDocument:
        doc = c.to_mongo()
        doc.pop("_id", None)
        result = await self._col.insert_one(doc)
        c.id = str(result.inserted_id)
        return c

    async def find_by_public_id(self, public_id: str) -> ComplaintDocument | None:
        doc = await self._col.find_one({"public_id": public_id})
        if not doc:
            return None
        return ComplaintDocument.from_mongo(doc)

    async def find_by_id(self, oid: str) -> ComplaintDocument | None:
        try:
            _id = ObjectId(oid)
        except Exception:
            return None
        doc = await self._col.find_one({"_id": _id})
        if not doc:
            return None
        return ComplaintDocument.from_mongo(doc)

    def _filter_query(
        self,
        base: dict,
        flt: ComplaintFilter | None,
    ) -> dict:
        q = dict(base)
        if flt is None:
            return q
        if flt.status:
            q["status"] = flt.status.value
        if flt.category:
            q["category"] = flt.category.value
        if flt.priority:
            q["priority"] = flt.priority.value
        if flt.date_from or flt.date_to:
            q["created_at"] = {}
            if flt.date_from:
                q["created_at"]["$gte"] = flt.date_from
            if flt.date_to:
                q["created_at"]["$lte"] = flt.date_to
        return q

    async def list_for_resident(
        self,
        resident_id: str,
        flt: ComplaintFilter | None = None,
    ) -> list[ComplaintDocument]:
        q = self._filter_query({"resident_id": resident_id}, flt)
        cursor = self._col.find(q).sort("created_at", -1)
        return [ComplaintDocument.from_mongo(d) async for d in cursor]

    async def list_all(self, flt: ComplaintFilter | None = None) -> list[ComplaintDocument]:
        q = self._filter_query({}, flt)
        cursor = self._col.find(q).sort("created_at", -1)
        return [ComplaintDocument.from_mongo(d) async for d in cursor]

    async def list_assigned(self, staff_id: str, flt: ComplaintFilter | None = None) -> list[ComplaintDocument]:
        q = self._filter_query({"assigned_staff_id": staff_id}, flt)
        cursor = self._col.find(q).sort("created_at", -1)
        return [ComplaintDocument.from_mongo(d) async for d in cursor]

    async def update(self, c: ComplaintDocument) -> None:
        assert c.id
        oid = ObjectId(c.id)
        doc = c.to_mongo()
        doc.pop("_id", None)
        await self._col.replace_one({"_id": oid}, doc)

    async def aggregate_category_counts(self) -> list[dict]:
        pipeline = [{"$group": {"_id": "$category", "count": {"$sum": 1}}}]
        return await self._col.aggregate(list(pipeline)).to_list(length=50)

    @staticmethod
    def utcnow() -> datetime:
        return datetime.now(timezone.utc)
