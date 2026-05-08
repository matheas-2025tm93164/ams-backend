from __future__ import annotations

import mimetypes
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import get_complaint_service, get_jwt_user, get_user_client
from app.api.schemas import AnalyticsResponse, ComplaintCreate, ComplaintPatchBody, ComplaintResponse, ReviewResponse
from app.application.complaint_service import ComplaintApplicationService
from app.config import get_settings
from app.domain.models import ComplaintDocument, JwtUser
from app.infrastructure.complaint_repository import ComplaintFilter
from app.infrastructure.user_client import UserServiceClient
from shared.enums import Category, ComplaintStatus, Priority, Role

router = APIRouter(tags=["complaints"])


def _to_response(c: ComplaintDocument) -> ComplaintResponse:
    assert c.id
    return ComplaintResponse(
        id=c.id,
        public_id=c.public_id,
        resident_id=c.resident_id,
        resident_name=None,
        category=c.category,
        priority=c.priority,
        description=c.description,
        status=c.status,
        assigned_staff_id=c.assigned_staff_id,
        assigned_staff_name=None,
        images=c.images,
        created_at=c.created_at,
        updated_at=c.updated_at,
        completed_at=c.completed_at,
        resident_feedback=c.resident_feedback,
        rating=c.rating,
    )


async def _enrich_responses(
    rows: list[ComplaintDocument],
    responses: list[ComplaintResponse],
    user: JwtUser,
    client: UserServiceClient,
) -> list[ComplaintResponse]:
    role = Role(user.role)
    if role == Role.RESIDENT:
        return responses
    ids: set[str] = set()
    for c in rows:
        ids.add(c.resident_id)
        if c.assigned_staff_id:
            ids.add(c.assigned_staff_id)
    profiles = await client.get_users_batch(list(ids))
    out: list[ComplaintResponse] = []
    for c, r in zip(rows, responses):
        rn = profiles.get(c.resident_id, {}).get("full_name")
        if isinstance(rn, str):
            pass
        else:
            rn = None
        an = None
        if c.assigned_staff_id:
            an = profiles.get(c.assigned_staff_id, {}).get("full_name")
            if not isinstance(an, str):
                an = None
        upd: dict = {"resident_name": rn}
        if role == Role.ADMIN:
            upd["assigned_staff_name"] = an
        out.append(r.model_copy(update=upd))
    return out


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
    users: Annotated[UserServiceClient, Depends(get_user_client)],
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
    base = [_to_response(c) for c in rows]
    return await _enrich_responses(rows, base, user, users)


@router.get("/complaints/{public_id}/attachments/{index}/file")
async def download_attachment_file(
    public_id: str,
    index: int,
    user: Annotated[JwtUser, Depends(get_jwt_user)],
    svc: Annotated[ComplaintApplicationService, Depends(get_complaint_service)],
) -> FileResponse:
    try:
        c = await svc.get_by_public_id(user, public_id)
    except PermissionError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Request failed")
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request failed")
    if index < 0 or index >= len(c.images):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request failed")
    settings = get_settings()
    root = Path(settings.upload_dir).resolve()
    raw = Path(c.images[index])
    path = raw if raw.is_absolute() else (root / raw)
    path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request failed")
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request failed")
    media = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(
        path,
        media_type=media,
        filename=path.name,
    )


@router.get("/complaints/{public_id}", response_model=ComplaintResponse)
async def get_complaint(
    public_id: str,
    user: Annotated[JwtUser, Depends(get_jwt_user)],
    svc: Annotated[ComplaintApplicationService, Depends(get_complaint_service)],
    users: Annotated[UserServiceClient, Depends(get_user_client)],
) -> ComplaintResponse:
    try:
        c = await svc.get_by_public_id(user, public_id)
    except PermissionError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Request failed")
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request failed")
    base = _to_response(c)
    enriched = await _enrich_responses([c], [base], user, users)
    return enriched[0]


@router.patch("/complaints/{public_id}", response_model=ComplaintResponse)
async def patch_complaint(
    public_id: str,
    body: ComplaintPatchBody,
    user: Annotated[JwtUser, Depends(get_jwt_user)],
    svc: Annotated[ComplaintApplicationService, Depends(get_complaint_service)],
    users: Annotated[UserServiceClient, Depends(get_user_client)],
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
            has_completion = (
                body.rating is not None or body.resident_feedback is not None
            )
            has_edit = (
                body.category is not None
                or body.priority is not None
                or body.description is not None
            )
            if body.status is not None:
                if has_completion or has_edit:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request failed")
                c = await svc.patch(user, public_id, status=body.status)
            elif has_completion:
                if has_edit:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request failed")
                c = await svc.patch(
                    user,
                    public_id,
                    resident_feedback=body.resident_feedback,
                    rating=body.rating,
                )
            elif has_edit:
                c = await svc.patch(
                    user,
                    public_id,
                    category=body.category,
                    priority=body.priority,
                    description=body.description,
                )
            else:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Request failed")
        b = _to_response(c)
        enriched = await _enrich_responses([c], [b], user, users)
        return enriched[0]
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
            "not_resolved",
            "empty_patch",
            "empty_patch_resident",
            "feedback_or_rating_required",
            "not_editable",
        ):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request failed")
        raise
    except PermissionError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Request failed")


async def _delete_complaint_core(
    public_id: str,
    user: JwtUser,
    svc: ComplaintApplicationService,
) -> None:
    try:
        await svc.delete(user, public_id)
    except ValueError as e:
        if str(e) == "not_found":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Request failed")
        if str(e) == "cannot_delete":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request failed")
        raise
    except PermissionError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Request failed")


@router.delete("/complaints/{public_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_complaint(
    public_id: str,
    user: Annotated[JwtUser, Depends(get_jwt_user)],
    svc: Annotated[ComplaintApplicationService, Depends(get_complaint_service)],
) -> None:
    await _delete_complaint_core(public_id, user, svc)


@router.post("/complaints/{public_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_complaint_post(
    public_id: str,
    user: Annotated[JwtUser, Depends(get_jwt_user)],
    svc: Annotated[ComplaintApplicationService, Depends(get_complaint_service)],
) -> None:
    await _delete_complaint_core(public_id, user, svc)


@router.post("/complaints/{public_id}/attachments", response_model=ComplaintResponse)
async def upload_attachment(
    public_id: str,
    user: Annotated[JwtUser, Depends(get_jwt_user)],
    svc: Annotated[ComplaintApplicationService, Depends(get_complaint_service)],
    users: Annotated[UserServiceClient, Depends(get_user_client)],
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
    ext_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    ext = ext_map.get(ct, ".bin")
    safe_name = f"{public_id}_{uuid.uuid4().hex}{ext}"
    path = Path(settings.upload_dir) / safe_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    rel = str(path)
    try:
        c = await svc.add_image_ref(user, public_id, rel)
        b = _to_response(c)
        enriched = await _enrich_responses([c], [b], user, users)
        return enriched[0]
    except PermissionError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Request failed")
    except ValueError as e:
        if str(e) == "not_found":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Request failed")
        if str(e) == "cannot_attach":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request failed")
        raise


@router.get("/reviews", response_model=list[ReviewResponse])
async def list_reviews(
    user: Annotated[JwtUser, Depends(get_jwt_user)],
    svc: Annotated[ComplaintApplicationService, Depends(get_complaint_service)],
    users: Annotated[UserServiceClient, Depends(get_user_client)],
    rating: int | None = Query(None, ge=1, le=5),
    staff_id: str | None = Query(None),
) -> list[ReviewResponse]:
    try:
        rows = await svc.list_reviews(user, rating=rating, staff_id=staff_id)
    except PermissionError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Request failed")
    ids: set[str] = set()
    for c in rows:
        ids.add(c.resident_id)
        if c.assigned_staff_id:
            ids.add(c.assigned_staff_id)
    profiles = await users.get_users_batch(list(ids))
    result: list[ReviewResponse] = []
    for c in rows:
        rn = profiles.get(c.resident_id, {}).get("full_name")
        an = None
        if c.assigned_staff_id:
            an = profiles.get(c.assigned_staff_id, {}).get("full_name")
        result.append(ReviewResponse(
            public_id=c.public_id,
            resident_name=rn if isinstance(rn, str) else None,
            assigned_staff_id=c.assigned_staff_id,
            assigned_staff_name=an if isinstance(an, str) else None,
            resident_feedback=c.resident_feedback,
            rating=c.rating or 0,
            completed_at=c.completed_at or c.updated_at,
        ))
    return result


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
