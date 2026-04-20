from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.complaint_service import ComplaintApplicationService
from app.domain.models import ComplaintDocument, JwtUser
from shared.enums import Category, ComplaintStatus, Priority, Role

_NOW = datetime.now(timezone.utc)


def _doc(
    *,
    status: ComplaintStatus = ComplaintStatus.PENDING,
    resident_id: str = "r1",
    public_id: str = "CMP-2026-ABCDEF",
) -> ComplaintDocument:
    return ComplaintDocument(
        id="507f1f77bcf86cd799439011",
        public_id=public_id,
        resident_id=resident_id,
        category=Category.PLUMBING,
        priority=Priority.MEDIUM,
        description="Leak under sink",
        status=status,
        assigned_staff_id=None,
        images=[],
        created_at=_NOW,
        updated_at=_NOW,
        completed_at=None,
        resident_feedback=None,
        rating=None,
    )


@pytest.mark.asyncio
@patch("app.application.complaint_service.get_settings")
async def test_delete_resident_pending(mock_settings: MagicMock) -> None:
    mock_settings.return_value = MagicMock(upload_dir="/tmp/ams-test-uploads")
    repo = AsyncMock()
    user_client = AsyncMock()
    c = _doc()
    repo.find_by_public_id = AsyncMock(return_value=c)
    repo.delete_by_id = AsyncMock(return_value=True)
    svc = ComplaintApplicationService(repo, user_client)
    u = JwtUser(id="r1", email="a@b.com", role=Role.RESIDENT.value)
    await svc.delete(u, c.public_id)
    repo.delete_by_id.assert_awaited_once_with(c.id)


@pytest.mark.asyncio
@patch("app.application.complaint_service.get_settings")
async def test_delete_resident_non_pending_raises(mock_settings: MagicMock) -> None:
    mock_settings.return_value = MagicMock(upload_dir="/tmp/ams-test-uploads")
    repo = AsyncMock()
    c = _doc(status=ComplaintStatus.IN_PROGRESS)
    repo.find_by_public_id = AsyncMock(return_value=c)
    svc = ComplaintApplicationService(repo, AsyncMock())
    u = JwtUser(id="r1", email="a@b.com", role=Role.RESIDENT.value)
    with pytest.raises(ValueError, match="cannot_delete"):
        await svc.delete(u, c.public_id)


@pytest.mark.asyncio
async def test_resident_patch_edit_pending_updates_fields() -> None:
    repo = AsyncMock()
    c = _doc()
    repo.find_by_public_id = AsyncMock(return_value=c)
    repo.update = AsyncMock()
    svc = ComplaintApplicationService(repo, AsyncMock())
    u = JwtUser(id="r1", email="a@b.com", role=Role.RESIDENT.value)
    out = await svc.patch(
        u,
        c.public_id,
        category=Category.ELECTRICAL,
        priority=Priority.HIGH,
        description="Updated details",
    )
    assert out.category == Category.ELECTRICAL
    assert out.priority == Priority.HIGH
    assert out.description == "Updated details"
    repo.update.assert_awaited()
