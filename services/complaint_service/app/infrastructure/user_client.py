from __future__ import annotations

import httpx

from app.config import Settings, get_settings


class UserServiceClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._base = self._settings.user_service_url.rstrip("/")

    async def get_user(self, user_id: str) -> dict | None:
        url = f"{self._base}/internal/users/{user_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
        if r.status_code != 200:
            return None
        return r.json()

    async def get_users_batch(self, user_ids: list[str]) -> dict[str, dict]:
        unique = list(dict.fromkeys(i for i in user_ids if i))
        if not unique:
            return {}
        url = f"{self._base}/internal/users/batch"
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(url, json={"ids": unique})
        if r.status_code != 200:
            return {}
        out: dict[str, dict] = {}
        for row in r.json():
            oid = row.get("id")
            if oid:
                out[str(oid)] = row
        return out
