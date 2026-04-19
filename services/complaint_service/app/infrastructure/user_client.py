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
