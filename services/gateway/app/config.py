from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    user_service_url: str = Field(default="http://localhost:8001")
    complaint_service_url: str = Field(default="http://localhost:8002")
    cors_origins: str = Field(
        default="http://localhost:5173",
        description="Comma-separated allow list",
    )

    def origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def get_settings() -> Settings:
    return Settings()
