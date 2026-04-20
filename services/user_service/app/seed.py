from __future__ import annotations

import os

from app.application.auth_service import hash_password
from app.domain.models import UserDocument
from app.infrastructure.user_repository import UserRepository
from shared.enums import Role


async def seed_demo_users(repo: UserRepository) -> None:
    if os.getenv("SEED_DEMO_USERS", "").lower() not in ("1", "true", "yes"):
        return
    demos = [
        (
            os.getenv("SEED_ADMIN_EMAIL", "admin@example.com"),
            os.getenv("SEED_ADMIN_PASSWORD", "Admin123!pass"),
            os.getenv("SEED_ADMIN_NAME", "Building Admin"),
            Role.ADMIN,
        ),
        (
            os.getenv("SEED_STAFF_EMAIL", "staff@example.com"),
            os.getenv("SEED_STAFF_PASSWORD", "Staff123!pass"),
            os.getenv("SEED_STAFF_NAME", "Maintenance Staff"),
            Role.MAINTENANCE_STAFF,
        ),
    ]
    now = UserRepository.utcnow()
    for email, password, name, role in demos:
        existing = await repo.find_by_email(email)
        if existing:
            continue
        user = UserDocument(
            id=None,
            email=email,
            password_hash=hash_password(password),
            full_name=name,
            role=role,
            created_at=now,
        )
        await repo.create(user)
