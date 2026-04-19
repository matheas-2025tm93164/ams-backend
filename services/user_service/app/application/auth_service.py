from __future__ import annotations

from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import Settings, get_settings
from app.domain.models import UserDocument, UserPublic
from app.infrastructure.user_repository import UserRepository
from shared.enums import Role
from shared.jwt_tokens import create_access_token

_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        _hasher.verify(password_hash, plain)
        return True
    except VerifyMismatchError:
        return False


class AuthService:
    def __init__(self, repo: UserRepository, settings: Settings | None = None) -> None:
        self._repo = repo
        self._settings = settings or get_settings()

    async def register_resident(
        self,
        email: str,
        password: str,
        full_name: str,
    ) -> tuple[UserPublic, str]:
        existing = await self._repo.find_by_email(email)
        if existing:
            raise ValueError("email_in_use")
        now = UserRepository.utcnow()
        user = UserDocument(
            id=None,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=Role.RESIDENT,
            created_at=now,
        )
        created = await self._repo.create(user)
        token = self._issue_token(created.id, created.email, created.role)
        return self._to_public(created), token

    async def login(self, email: str, password: str) -> tuple[UserPublic, str]:
        user = await self._repo.find_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("invalid_credentials")
        assert user.id
        token = self._issue_token(user.id, user.email, user.role)
        return self._to_public(user), token

    async def get_user(self, user_id: str) -> UserPublic | None:
        user = await self._repo.find_by_id(user_id)
        if not user or not user.id:
            return None
        return self._to_public(user)

    def _issue_token(self, user_id: str, email: str, role: Role) -> str:
        delta = timedelta(minutes=self._settings.access_token_expire_minutes)
        return create_access_token(
            {"sub": user_id, "email": email, "role": role.value},
            self._settings.jwt_secret,
            self._settings.jwt_algorithm,
            delta,
        )

    @staticmethod
    def _to_public(user: UserDocument) -> UserPublic:
        assert user.id
        return UserPublic(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
        )
