from __future__ import annotations

from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import Settings, get_settings
from app.domain.models import UserDocument, UserPublic
from app.infrastructure.user_repository import UserRepository
from shared.enums import AccountStatus, Role
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

    async def login(self, email: str, password: str) -> tuple[UserPublic, str]:
        user = await self._repo.find_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("invalid_credentials")
        if user.account_status != AccountStatus.ACTIVE:
            raise ValueError("invalid_credentials")
        assert user.id
        token = self._issue_token(user.id, user.email, user.role)
        return self.to_public(user), token

    async def get_user(self, user_id: str) -> UserPublic | None:
        user = await self._repo.find_by_id(user_id)
        if not user or not user.id:
            return None
        return self.to_public(user)

    async def onboard_staff(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        address: str,
        phone: str,
        aadhar: str,
    ) -> UserPublic:
        existing = await self._repo.find_by_email(email)
        if existing:
            raise ValueError("email_in_use")
        now = UserRepository.utcnow()
        user = UserDocument(
            id=None,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=Role.MAINTENANCE_STAFF,
            created_at=now,
            account_status=AccountStatus.ACTIVE,
            phone=phone,
            address=address,
            aadhar=aadhar,
            family_members=[],
        )
        created = await self._repo.create(user)
        return self.to_public(created)

    async def onboard_resident(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        phone: str,
        aadhar: str,
        family_members: list[str],
    ) -> UserPublic:
        existing = await self._repo.find_by_email(email)
        if existing:
            raise ValueError("email_in_use")
        primary_lower = full_name.strip().casefold()
        for m in family_members:
            if m.strip().casefold() == primary_lower:
                raise ValueError("family_duplicate_primary")
        now = UserRepository.utcnow()
        user = UserDocument(
            id=None,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=Role.RESIDENT,
            created_at=now,
            account_status=AccountStatus.ACTIVE,
            phone=phone,
            address=None,
            aadhar=aadhar,
            family_members=family_members,
        )
        created = await self._repo.create(user)
        return self.to_public(created)

    async def update_staff(
        self,
        user_id: str,
        *,
        full_name: str,
        address: str,
        phone: str,
        aadhar: str | None,
        password: str | None,
    ) -> UserPublic:
        user = await self._repo.find_by_id(user_id)
        if not user or not user.id:
            raise ValueError("not_found")
        if user.role != Role.MAINTENANCE_STAFF:
            raise ValueError("wrong_role")
        patch: dict[str, object] = {
            "full_name": full_name.strip(),
            "address": address.strip(),
            "phone": phone.strip(),
        }
        if aadhar is not None:
            patch["aadhar"] = aadhar
        if password:
            patch["password_hash"] = hash_password(password)
        ok = await self._repo.update_user_fields(user_id, patch)
        if not ok:
            raise ValueError("not_found")
        updated = await self._repo.find_by_id(user_id)
        assert updated and updated.id
        return self.to_public(updated)

    async def update_resident(
        self,
        user_id: str,
        *,
        full_name: str,
        phone: str,
        aadhar: str | None,
        family_members: list[str],
        password: str | None,
    ) -> UserPublic:
        user = await self._repo.find_by_id(user_id)
        if not user or not user.id:
            raise ValueError("not_found")
        if user.role != Role.RESIDENT:
            raise ValueError("wrong_role")
        primary_lower = full_name.strip().casefold()
        for m in family_members:
            if m.strip().casefold() == primary_lower:
                raise ValueError("family_duplicate_primary")
        patch: dict[str, object] = {
            "full_name": full_name.strip(),
            "phone": phone.strip(),
            "family_members": family_members,
        }
        if aadhar is not None:
            patch["aadhar"] = aadhar
        if password:
            patch["password_hash"] = hash_password(password)
        ok = await self._repo.update_user_fields(user_id, patch)
        if not ok:
            raise ValueError("not_found")
        updated = await self._repo.find_by_id(user_id)
        assert updated and updated.id
        return self.to_public(updated)

    async def deactivate_user(self, user_id: str) -> None:
        user = await self._repo.find_by_id(user_id)
        if not user or not user.id:
            raise ValueError("not_found")
        if user.role == Role.ADMIN:
            raise ValueError("cannot_deactivate_admin")
        ok = await self._repo.set_account_status(user.id, AccountStatus.RESIGNED)
        if not ok:
            raise ValueError("not_found")

    async def activate_user(self, user_id: str) -> None:
        user = await self._repo.find_by_id(user_id)
        if not user or not user.id:
            raise ValueError("not_found")
        if user.role == Role.ADMIN:
            raise ValueError("cannot_activate_admin")
        ok = await self._repo.set_account_status(user.id, AccountStatus.ACTIVE)
        if not ok:
            raise ValueError("not_found")

    def _issue_token(self, user_id: str, email: str, role: Role) -> str:
        delta = timedelta(minutes=self._settings.access_token_expire_minutes)
        return create_access_token(
            {"sub": user_id, "email": email, "role": role.value},
            self._settings.jwt_secret,
            self._settings.jwt_algorithm,
            delta,
        )

    @staticmethod
    def to_public(user: UserDocument) -> UserPublic:
        assert user.id
        return UserPublic(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            account_status=user.account_status,
        )
