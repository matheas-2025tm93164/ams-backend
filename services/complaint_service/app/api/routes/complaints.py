from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.api.deps import get_complaint_service, get_jwt_user
from app.api.schemas import AnalyticsResponse, ComplaintCreate, ComplaintPatchBody, ComplaintResponse
from app.application.complaint_service import ComplaintApplicationService
from app.config import get_settings
from app.domain.models import ComplaintDocument, JwtUser
from app.infrastructure.complaint_repository import ComplaintFilter
from shared.enums import Category, ComplaintStatus, Priority, Role

router = APIRouter(tags=["complaints"])


def _to_response(c: ComplaintDocument) -> ComplaintResponse:
    assert c.id
    return ComplaintResponse(
        id=c.id,
        public_id=c.public_id,
        resident_id=c.resident_id,
        category=c.category,
        priority=c.priority,
        description=c.description,
        status=c.status,
        assigned_staff_id=c.assigned_staff_id,
        images=c.images,
        created_at=c.created_at,
        updated_at=c.updated_at,
        completed_at=c.completed_at,
        resident_feedback=c.resident_feedback,
        rating=c.rating,
    )


@router.post("/complaints", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def create_complaint(
    body: ComplaintCreate,
    user: Annotated[JwtUser, Depends(get_jwt_user)],
    svc: Annotated[ComplaintApplicationService, Depends(get_complaint_service)],
) -> ComplaintResponse:
    try:
        c = await svc.create(user, body.category, body.priority, body.description)
        return _to_response(c)
    except PermissionError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Request failed")


@router.get("/complaints", response_model=list[ComplaintResponse])
async def list_complaints(
    user: Annotated[JwtUser, Depends(get_jwt_user)],
    svc: Annotated[ComplaintApplicationService, Depends(get_complaint_service)],
    status_filter: ComplaintStatus | None = Query(None, alias="status"),
    category: Category | None = None,
    priority: Priority | None = None,
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
) -> list[ComplaintResponse]:
    flt = ComplaintFilter(
        status=status_filter,
        category=category,
        priority=priority,
        date_from=date_from,
        date_to=date_to,
    )
    rows = await svc.list_complaints(user, flt)
    return [_to_response(c) for c in rows]


@router.get("/complaints/{public_id}", response_model=ComplaintResponse)
async def get_complaint(
    public_id: str,
    user: Annotated[JwtUser, Depends(get_jwt_user)],
    svc: Annotated[ComplaintApplicationService, Depends(get_complaint_service)],
) -> ComplaintResponse:
    try:
        c = await svc.get_by_public_id(user, public_id)
    except PermissionError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Request failed")
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request failed")
    return _to_response(c)


@router.patch("/complaints/{public_id}", response_model=ComplaintResponse)
async def patch_complaint(
    public_id: str,
    body: ComplaintPatchBody,
    user: Annotated[JwtUser, Depends(get_jwt_user)],
    svc: Annotated[ComplaintApplicationService, Depends(get_complaint_service)],
) -> ComplaintResponse:
    role = Role(user.role)
    try:
        if role == Role.ADMIN:
            if (
                body.assigned_staff_id is None
                and body.category is None
                and body.priority is None
            ):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Request failed")
            c = await svc.patch(
                user,
                public_id,
                assigned_staff_id=body.assigned_staff_id,
                category=body.category,
                priority=body.priority,
            )
        elif role == Role.MAINTENANCE_STAFF:
            if body.status is None:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Request failed")
            c = await svc.patch(user, public_id, status=body.status)
        else:
            if body.resident_feedback is None and body.rating is None:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Request failed")
            c = await svc.patch(
                user,
                public_id,
                resident_feedback=body.resident_feedback,
                rating=body.rating,
            )
        return _to_response(c)
    except ValueError as e:
        code = str(e)
        if code == "not_found":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Request failed")
        if code == "invalid_assignee":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request failed")
        if code in (
            "invalid_transition",
            "invalid_status",
            "status_required",
            "not_ready_for_completion",
            "empty_patch",
            "feedback_or_rating_required",
        ):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request failed")
        raise
    except PermissionError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Request failed")


@router.post("/complaints/{public_id}/attachments", response_model=ComplaintResponse)
async def upload_attachment(
    public_id: str,
    user: Annotated[JwtUser, Depends(get_jwt_user)],
    svc: Annotated[ComplaintApplicationService, Depends(get_complaint_service)],
    file: UploadFile = File(...),
) -> ComplaintResponse:
    settings = get_settings()
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Request failed")
    ct = file.content_type or ""
    allowed = {x.strip() for x in settings.allowed_image_types.split(",")}
    if ct not in allowed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request failed")
    import uuid
    from pathlib import Path

    safe_name = f"{public_id}_{uuid.uuid4().hex}.bin"
    path = Path(settings.upload_dir) / safe_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    rel = str(path)
    try:
        c = await svc.add_image_ref(user, public_id, rel)
        return _to_response(c)
    except PermissionError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Request failed")
    except ValueError as e:
        if str(e) == "not_found":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Request failed")
        if str(e) == "cannot_attach":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request failed")
        raise


@router.get("/analytics/summary", response_model=AnalyticsResponse)
async def analytics_summary(
    user: Annotated[JwtUser, Depends(get_jwt_user)],
    svc: Annotated[ComplaintApplicationService, Depends(get_complaint_service)],
) -> AnalyticsResponse:
    try:
        data = await svc.analytics(user)
        return AnalyticsResponse(by_category=data["by_category"])
    except PermissionError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Request failed")
