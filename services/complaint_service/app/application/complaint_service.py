from __future__ import annotations

import re
import secrets
from datetime import datetime
from pathlib import Path

from app.config import get_settings
from app.domain.models import ComplaintDocument, JwtUser
from app.infrastructure.complaint_repository import ComplaintFilter, ComplaintRepository
from app.infrastructure.user_client import UserServiceClient
from shared.enums import Category, ComplaintStatus, Priority, Role


def generate_public_id(year: int | None = None) -> str:
    y = year or datetime.now().year
    suffix = secrets.token_hex(3).upper()
    return f"CMP-{y}-{suffix}"


class ComplaintApplicationService:
    def __init__(
        self,
        repo: ComplaintRepository,
        user_client: UserServiceClient,
    ) -> None:
        self._repo = repo
        self._user_client = user_client

    async def create(
        self,
        user: JwtUser,
        category: Category,
        priority: Priority,
        description: str,
    ) -> ComplaintDocument:
        if user.role != Role.RESIDENT.value:
            raise PermissionError("only_residents_create")
        now = ComplaintRepository.utcnow()
        public_id = generate_public_id()
        for _ in range(5):
            existing = await self._repo.find_by_public_id(public_id)
            if not existing:
                break
            public_id = generate_public_id()
        c = ComplaintDocument(
            id=None,
            public_id=public_id,
            resident_id=user.id,
            category=category,
            priority=priority,
            description=description.strip(),
            status=ComplaintStatus.PENDING,
            assigned_staff_id=None,
            images=[],
            created_at=now,
            updated_at=now,
            completed_at=None,
            resident_feedback=None,
            rating=None,
        )
        return await self._repo.create(c)

    async def list_complaints(
        self,
        user: JwtUser,
        flt: ComplaintFilter,
    ) -> list[ComplaintDocument]:
        role = Role(user.role)
        if role == Role.ADMIN:
            return await self._repo.list_all(flt)
        if role == Role.MAINTENANCE_STAFF:
            return await self._repo.list_assigned(user.id, flt)
        return await self._repo.list_for_resident(user.id, flt)

    async def get_by_public_id(self, user: JwtUser, public_id: str) -> ComplaintDocument | None:
        if not re.match(r"^CMP-\d{4}-[A-F0-9]{6}$", public_id):
            return None
        c = await self._repo.find_by_public_id(public_id)
        if not c:
            return None
        if not self._can_read(user, c):
            raise PermissionError("forbidden")
        return c

    def _can_read(self, user: JwtUser, c: ComplaintDocument) -> bool:
        role = Role(user.role)
        if role == Role.ADMIN:
            return True
        if role == Role.MAINTENANCE_STAFF:
            return c.assigned_staff_id == user.id
        return c.resident_id == user.id

    async def patch(
        self,
        user: JwtUser,
        public_id: str,
        *,
        assigned_staff_id: str | None = None,
        category: Category | None = None,
        priority: Priority | None = None,
        description: str | None = None,
        status: ComplaintStatus | None = None,
        resident_feedback: str | None = None,
        rating: int | None = None,
    ) -> ComplaintDocument:
        c = await self._repo.find_by_public_id(public_id)
        if not c:
            raise ValueError("not_found")
        role = Role(user.role)

        if role == Role.ADMIN:
            if (
                assigned_staff_id is None
                and category is None
                and priority is None
            ):
                raise ValueError("empty_patch")
            if assigned_staff_id is not None:
                u = await self._user_client.get_user(assigned_staff_id)
                if (
                    not u
                    or u.get("role") != Role.MAINTENANCE_STAFF.value
                    or u.get("account_status") == "resigned"
                ):
                    raise ValueError("invalid_assignee")
                c.assigned_staff_id = assigned_staff_id
            if category is not None:
                c.category = category
            if priority is not None:
                c.priority = priority
            c.updated_at = ComplaintRepository.utcnow()
            await self._repo.update(c)
            return c

        if role == Role.MAINTENANCE_STAFF:
            if c.assigned_staff_id != user.id:
                raise PermissionError("forbidden")
            if status is None:
                raise ValueError("status_required")
            self._apply_staff_status(c, status)
            c.updated_at = ComplaintRepository.utcnow()
            await self._repo.update(c)
            return c

        if role == Role.RESIDENT:
            if c.resident_id != user.id:
                raise PermissionError("forbidden")
            if status is not None:
                if status != ComplaintStatus.PENDING:
                    raise ValueError("invalid_status")
                if c.status != ComplaintStatus.RESOLVED:
                    raise ValueError("not_resolved")
                c.status = ComplaintStatus.PENDING
                c.updated_at = ComplaintRepository.utcnow()
                await self._repo.update(c)
                return c
            has_completion = resident_feedback is not None or rating is not None
            has_edit = (
                category is not None or priority is not None or description is not None
            )
            if has_completion:
                if c.status != ComplaintStatus.RESOLVED:
                    raise ValueError("not_ready_for_completion")
                if resident_feedback is None and rating is None:
                    raise ValueError("feedback_or_rating_required")
                c.status = ComplaintStatus.COMPLETED
                c.completed_at = ComplaintRepository.utcnow()
                if resident_feedback is not None:
                    c.resident_feedback = resident_feedback.strip()[:4000]
                if rating is not None:
                    c.rating = rating
                c.updated_at = ComplaintRepository.utcnow()
                await self._repo.update(c)
                return c
            if has_edit:
                if c.status != ComplaintStatus.PENDING:
                    raise ValueError("not_editable")
                if category is not None:
                    c.category = category
                if priority is not None:
                    c.priority = priority
                if description is not None:
                    c.description = description.strip()[:8000]
                c.updated_at = ComplaintRepository.utcnow()
                await self._repo.update(c)
                return c
            raise ValueError("empty_patch_resident")

        raise PermissionError("forbidden")

    def _apply_staff_status(self, c: ComplaintDocument, new_status: ComplaintStatus) -> None:
        if new_status == ComplaintStatus.COMPLETED:
            raise ValueError("invalid_status")
        current = c.status
        if new_status == current:
            return
        if current == ComplaintStatus.PENDING and new_status == ComplaintStatus.IN_PROGRESS:
            c.status = new_status
            return
        if current == ComplaintStatus.IN_PROGRESS and new_status == ComplaintStatus.RESOLVED:
            c.status = new_status
            return
        if current == ComplaintStatus.RESOLVED and new_status == ComplaintStatus.PENDING:
            c.status = new_status
            return
        raise ValueError("invalid_transition")

    async def delete(self, user: JwtUser, public_id: str) -> None:
        c = await self._repo.find_by_public_id(public_id)
        if not c:
            raise ValueError("not_found")
        role = Role(user.role)
        if role == Role.RESIDENT:
            if c.resident_id != user.id:
                raise PermissionError("forbidden")
            if c.status != ComplaintStatus.PENDING:
                raise ValueError("cannot_delete")
        elif role == Role.ADMIN:
            pass
        else:
            raise PermissionError("forbidden")
        settings = get_settings()
        root = Path(settings.upload_dir).resolve()
        for raw in c.images:
            pth = Path(raw)
            pth = pth if pth.is_absolute() else (root / pth)
            try:
                resolved = pth.resolve()
                resolved.relative_to(root)
            except ValueError:
                continue
            if resolved.is_file():
                resolved.unlink()
        if not c.id:
            raise ValueError("not_found")
        if not await self._repo.delete_by_id(c.id):
            raise ValueError("not_found")

    async def add_image_ref(self, user: JwtUser, public_id: str, filename: str) -> ComplaintDocument:
        c = await self._repo.find_by_public_id(public_id)
        if not c:
            raise ValueError("not_found")
        if Role(user.role) != Role.RESIDENT or c.resident_id != user.id:
            raise PermissionError("forbidden")
        if c.status != ComplaintStatus.PENDING:
            raise ValueError("cannot_attach")
        c.images.append(filename)
        c.updated_at = ComplaintRepository.utcnow()
        await self._repo.update(c)
        return c

    async def list_reviews(
        self,
        user: JwtUser,
        rating: int | None = None,
        staff_id: str | None = None,
    ) -> list[ComplaintDocument]:
        role = Role(user.role)
        if role == Role.ADMIN:
            return await self._repo.list_reviews(staff_id=staff_id, rating=rating)
        if role == Role.MAINTENANCE_STAFF:
            return await self._repo.list_reviews(staff_id=user.id, rating=rating)
        raise PermissionError("forbidden")

    async def analytics(self, user: JwtUser) -> dict:
        if Role(user.role) != Role.ADMIN:
            raise PermissionError("forbidden")
        rows = await self._repo.aggregate_category_counts()
        return {"by_category": [{"category": r["_id"], "count": r["count"]} for r in rows]}
