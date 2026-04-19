from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


class MongoConnection:
    def __init__(self, uri: str, db_name: str) -> None:
        self._client = AsyncIOMotorClient(uri)
        self._db: AsyncIOMotorDatabase = self._client[db_name]

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db

    def close(self) -> None:
        self._client.close()
