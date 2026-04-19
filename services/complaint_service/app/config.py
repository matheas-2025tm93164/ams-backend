from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongo_uri: str = Field(default="mongodb://localhost:27017")
    mongo_db: str = Field(default="complaints_db")
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = Field(default="HS256")
    user_service_url: str = Field(default="http://localhost:8001")
    upload_dir: str = Field(default="/data/uploads")
    max_upload_bytes: int = Field(default=2_097_152, ge=1024, le=10_485_760)
    allowed_image_types: str = Field(default="image/jpeg,image/png,image/webp")


def get_settings() -> Settings:
    return Settings()
