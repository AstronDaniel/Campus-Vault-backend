from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Header, Query, Body
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from hashlib import sha256 as _sha256
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
import base64

from app.api.deps import db_session, get_current_user
from app.core.config import get_settings
from app.models.resource import Resource
from app.models.resource_bookmark import ResourceBookmark
from app.models.resource_comment import ResourceComment
from app.models.resource_rating import ResourceRating
from app.models.course_unit import CourseUnit
from app.models.resource_download import ResourceDownloadEvent
from app.schemas.resource import (
    ResourceRead, ResourceDuplicateInfo, ResourceUpdate,
    ResourceLinkRequest, ResourcesBulkDeleteRequest, ResourcesBulkDeleteResponse,
    CommentCreate, CommentRead, RatingCreate, ResourceListResponse,
)
from app.models.user import User
from app.utils.storage import get_storage
from app.services.activity_service import ActivityService
from app.models.activity import ActivityType

router = APIRouter(prefix="/api/v1/resources", tags=["Resources"])
settings = get_settings()


# Pydantic model for mobile upload (JSON-based instead of multipart)
class MobileUploadRequest(BaseModel):
    course_unit_id: int
    filename: str
    content_type: str
    file_base64: str  # Base64 encoded file content
    title: Optional[str] = None
    description: Optional[str] = None
    resource_type: str = "notes"


# Simple endpoint for mobile to test auth is working before attempting upload
@router.get("/mobile/ping")
async def mobile_ping(user: User = Depends(get_current_user)):
    """Simple endpoint for mobile clients to verify auth works. Returns user info."""
    return {
        "status": "ok",
        "user_id": user.id,
        "username": user.username,
        "message": "Auth is working! You can upload."
    }


# Mobile-friendly upload using JSON with base64-encoded file (avoids multipart issues on Vercel)
@router.post("/mobile/upload", response_model=ResourceRead, status_code=status.HTTP_201_CREATED)
async def mobile_upload_resource(
    payload: MobileUploadRequest,
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
):
    """
    Mobile-friendly upload endpoint that accepts JSON with base64-encoded file.
    This avoids multipart/form-data issues that can occur with some cloud providers.
    """
    # Validate course unit exists
    if not db.get(CourseUnit, payload.course_unit_id):
        raise HTTPException(status_code=400, detail="Course unit not found")
    
    # Decode base64 content
    try:
        content = base64.b64decode(payload.file_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 file content")
    
    # Basic size check
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail="File too large")
    
    # Compute SHA256 for deduplication
    h = _sha256()
    h.update(content)
    digest = h.hexdigest()
    
    # Check for duplicate
    existing = db.query(Resource).filter(Resource.sha256 == digest).first()
    if existing:
        raise HTTPException(status_code=409, detail={
            "message": "Duplicate content detected",
            "resource": {
                "id": existing.id,
                "course_unit_id": existing.course_unit_id,
                "uploader_id": existing.uploader_id,
                "title": existing.title,
                "description": existing.description,
                "filename": existing.filename,
                "content_type": existing.content_type,
                "size_bytes": existing.size_bytes,
                "sha256": existing.sha256,
                "storage_path": existing.storage_path,
                "url": existing.url,
                "created_at": existing.created_at.isoformat(),
            }
        })
    
    # Save using storage backend
    content_type = payload.content_type.lower()
    storage = get_storage()
    storage_path, url = storage.save_resource(
        course_unit_id=payload.course_unit_id,
        digest=digest,
        filename=payload.filename,
        content_type=content_type,
        content=content
    )
    
    resource = Resource(
        course_unit_id=payload.course_unit_id,
        uploader_id=user.id,
        title=payload.title,
        description=payload.description,
        resource_type=payload.resource_type,
        filename=payload.filename,
        content_type=content_type,
        size_bytes=len(content),
        sha256=digest,
        storage_path=storage_path,
        url=url,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    
    # Log activity
    ActivityService.log_activity(
        db=db,
        user_id=user.id,
        activity_type=ActivityType.resource_uploaded,
        description=f"Uploaded resource: {resource.title}",
        details={
            "resource_id": resource.id,
            "course_unit_id": resource.course_unit_id,
            "filename": resource.filename,
            "size_bytes": resource.size_bytes,
            "content_type": resource.content_type,
            "upload_method": "mobile_base64"
        }
    )
    
    return resource


@router.post("/upload", response_model=ResourceRead, status_code=status.HTTP_201_CREATED)
async def upload_resource(
    course_unit_id: int = Form(...),
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    resource_type: str = Form(default="notes"),  # 'notes', 'past_paper', 'assignment', etc.
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
):
    # Validate course unit exists
    if not db.get(CourseUnit, course_unit_id):
        raise HTTPException(status_code=400, detail="Course unit not found")

    content = await file.read()
    # Basic size check
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail="File too large")

    # Compute SHA256 of content for deduplication
    h = _sha256()
    h.update(content)
    digest = h.hexdigest()

    # Check duplicate within same course unit
    # existing = db.query(Resource).filter(Resource.course_unit_id == course_unit_id, Resource.sha256 == digest).first()
    #check if the same file (by sha256) already exists in any course unit
    # if so, we can link to the same storage_path and url to save space
    existing = db.query(Resource).filter(Resource.sha256 == digest).first()

    if existing:
        # Return 409 with existing resource info
        raise HTTPException(status_code=409, detail={
            "message": "Duplicate content detected",
            "resource": {
                "id": existing.id,
                "course_unit_id": existing.course_unit_id,
                "uploader_id": existing.uploader_id,
                "title": existing.title,
                "description": existing.description,
                "filename": existing.filename,
                "content_type": existing.content_type,
                "size_bytes": existing.size_bytes,
                "sha256": existing.sha256,
                "storage_path": existing.storage_path,
                "url": existing.url,
                "created_at": existing.created_at.isoformat(),
            }
        })

    # Save using storage backend
    content_type = (file.content_type or "application/octet-stream").lower()
    storage = get_storage()
    storage_path, url = storage.save_resource(course_unit_id=course_unit_id, digest=digest, filename=file.filename, content_type=content_type, content=content)

    resource = Resource(
        course_unit_id=course_unit_id,
        uploader_id=user.id,
        title=title,
        description=description,
        resource_type=resource_type,
        filename=file.filename or digest,
        content_type=content_type,
        size_bytes=len(content),
        sha256=digest,
        storage_path=storage_path,
        url=url,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    # After successful upload, log the activity
    ActivityService.log_activity(
        db=db,
        user_id=user.id,
        activity_type=ActivityType.resource_uploaded,
        description=f"Uploaded resource: {resource.title}",
        details={
            "resource_id": resource.id,
            "course_unit_id": resource.course_unit_id,
            "filename": resource.filename,
            "size_bytes": resource.size_bytes,
            "content_type": resource.content_type,
        }
    )

    return resource


@router.post("/check-duplicate", response_model=ResourceDuplicateInfo)
async def check_duplicate(
    course_unit_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
):
    if not db.get(CourseUnit, course_unit_id):
        raise HTTPException(status_code=400, detail="Course unit not found")

    content = await file.read()
    h = _sha256()
    h.update(content)
    digest = h.hexdigest()

    existing = db.query(Resource).filter(Resource.course_unit_id == course_unit_id, Resource.sha256 == digest).first()
    if existing:
        from app.schemas.resource import ResourceRead
        return ResourceDuplicateInfo(duplicate=True, existing=ResourceRead.model_validate(existing))
    return ResourceDuplicateInfo(duplicate=False, existing=None)


@router.get("", response_model=ResourceListResponse)
def list_resources(
    course_unit_id: int | None = None,
    uploader_id: int | None = None,
    resource_type: str | None = None,  # Filter by resource type: 'notes', 'past_paper', etc.
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(db_session),
    # Temporarily make this endpoint public for testing
    # user: User = Depends(get_current_user),
):
    q = db.query(Resource)
    if course_unit_id is not None:
        q = q.filter(Resource.course_unit_id == course_unit_id)
    if uploader_id is not None:
        q = q.filter(Resource.uploader_id == uploader_id)
    if resource_type is not None:
        q = q.filter(Resource.resource_type == resource_type)
    total = q.count()
    items = q.order_by(Resource.created_at.desc()).offset(offset).limit(limit).all()
    # Calculate average rating for each resource
    for item in items:
        item.average_rating = round(item.rating_sum / item.rating_count, 2) if item.rating_count > 0 else 0.0
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{resource_id}", response_model=ResourceRead)
def get_resource(resource_id: int, db: Session = Depends(db_session), user: User = Depends(get_current_user)):
    r = db.get(Resource, resource_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resource not found")
    # Check if user has bookmarked this resource
    r.is_bookmarked = db.query(ResourceBookmark).filter(
        ResourceBookmark.user_id == user.id,
        ResourceBookmark.resource_id == resource_id
    ).first() is not None
    # Get user's rating for this resource
    user_rating_obj = db.query(ResourceRating).filter(
        ResourceRating.user_id == user.id,
        ResourceRating.resource_id == resource_id
    ).first()
    r.user_rating = user_rating_obj.rating if user_rating_obj else None
    # Calculate average rating
    r.average_rating = round(r.rating_sum / r.rating_count, 2) if r.rating_count > 0 else 0.0
    return r


@router.patch("/{resource_id}", response_model=ResourceRead)
def update_resource(resource_id: int, payload: ResourceUpdate, db: Session = Depends(db_session), user: User = Depends(get_current_user)):
    r = db.get(Resource, resource_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resource not found")
    if r.uploader_id != user.id:
        raise HTTPException(status_code=403, detail="You can only update your own resources")

    if payload.title is not None:
        r.title = payload.title
    if payload.description is not None:
        r.description = payload.description
    if payload.resource_type is not None:
        r.resource_type = payload.resource_type

    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(
    resource_id: int,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
):
    r = db.get(Resource, resource_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resource not found")

    # Owner can delete. Admin (API key) can delete any.
    if r.uploader_id != user.id:
        if not settings.API_KEY or x_api_key != settings.API_KEY:
            raise HTTPException(status_code=403, detail="Not authorized to delete this resource")

    # Delete from storage if this is the last reference
    refs = db.query(Resource).filter(Resource.storage_path == r.storage_path, Resource.id != r.id).count()
    if refs == 0:
        try:
            get_storage().delete(r.storage_path)
        except Exception:
            pass

    db.delete(r)
    db.commit()

    # After successful deletion, log the activity
    ActivityService.log_activity(
        db=db,
        user_id=user.id,
        activity_type=ActivityType.resource_deleted,
        description=f"Deleted resource: {r.title}",
        details={"resource_id": resource_id}
    )

    return


@router.post("/{resource_id}/download", response_model=ResourceRead)
def mark_download(resource_id: int, db: Session = Depends(db_session), user: User = Depends(get_current_user)):
    r = db.get(Resource, resource_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resource not found")
    r.download_count = (r.download_count or 0) + 1
    r.last_download_at = datetime.utcnow()
    db.add(r)
    db.add(ResourceDownloadEvent(resource_id=r.id, user_id=user.id))
    db.commit()
    db.refresh(r)
    return r


@router.get("/{resource_id}/download")
def download_resource(resource_id: int, db: Session = Depends(db_session), user: User = Depends(get_current_user)):
    r = db.get(Resource, resource_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resource not found")
    # increment counters
    r.download_count = (r.download_count or 0) + 1
    r.last_download_at = datetime.utcnow()
    db.add(r)
    db.add(ResourceDownloadEvent(resource_id=r.id, user_id=user.id))
    db.commit()

    storage = get_storage()
    resolution = storage.resolve_download(r.storage_path, r.url or "")
    if resolution.kind == "path":
        # Local file path, stream it
        abs_path = resolution.value
        if not Path(abs_path).exists():
            raise HTTPException(status_code=404, detail="File missing on server")
        return FileResponse(path=abs_path, media_type=r.content_type, filename=r.filename)
    else:
        # Redirect to remote URL (e.g., Google Drive)
        return RedirectResponse(url=resolution.value, status_code=302)

    # After successful download, log the activity
    ActivityService.log_activity(
        db=db,
        user_id=user.id,
        activity_type=ActivityType.resource_downloaded,
        description=f"Downloaded resource: {r.title}",
        details={
            "resource_id": r.id,
            "content_type": r.content_type,
            "size_bytes": r.size_bytes
        }
    )


@router.post("/{existing_id}/link", response_model=ResourceRead)
def link_existing_resource(
    existing_id: int,
    payload: ResourceLinkRequest,
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
):
    existing = db.get(Resource, existing_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Resource not found")
    if not db.get(CourseUnit, payload.course_unit_id):
        raise HTTPException(status_code=400, detail="Course unit not found")
    # avoid duplicate row if same hash already present for target course_unit
    dup = (
        db.query(Resource)
        .filter(Resource.course_unit_id == payload.course_unit_id, Resource.sha256 == existing.sha256)
        .first()
    )
    if dup:
        return dup
    r = Resource(
        course_unit_id=payload.course_unit_id,
        uploader_id=user.id,
        title=payload.title if payload.title is not None else existing.title,
        description=payload.description if payload.description is not None else existing.description,
        filename=existing.filename,
        content_type=existing.content_type,
        size_bytes=existing.size_bytes,
        sha256=existing.sha256,
        storage_path=existing.storage_path,
        url=existing.url,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.post("/{resource_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def add_comment(resource_id: int, payload: CommentCreate, db: Session = Depends(db_session), user: User = Depends(get_current_user)):
    r = db.get(Resource, resource_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resource not found")
    c = ResourceComment(resource_id=resource_id, user_id=user.id, body=payload.body)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.get("/trending", response_model=ResourceListResponse)
def trending_resources(
    course_unit_id: int | None = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
):
    q = db.query(Resource)
    if course_unit_id is not None:
        q = q.filter(Resource.course_unit_id == course_unit_id)
    total = q.count()
    items = q.order_by(desc(Resource.download_count), desc(Resource.last_download_at), desc(Resource.created_at)).offset(offset).limit(limit).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/search", response_model=ResourceListResponse)
def search_resources(
    q: str,
    course_unit_id: int | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
):
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query too short")
    term = f"%{q.strip()}%"
    base = db.query(Resource)
    if course_unit_id is not None:
        base = base.filter(Resource.course_unit_id == course_unit_id)
    total = base.filter(
        or_(
            Resource.title.ilike(term),
            Resource.description.ilike(term),
            Resource.filename.ilike(term),
        )
    ).count()
    items = (
        base.filter(
            or_(
                Resource.title.ilike(term),
                Resource.description.ilike(term),
                Resource.filename.ilike(term),
            )
        )
        .order_by(desc(Resource.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{resource_id}/comments", response_model=list[CommentRead])
def list_comments(resource_id: int, db: Session = Depends(db_session), user: User = Depends(get_current_user)):
    comments = (
        db.query(ResourceComment)
        .filter(ResourceComment.resource_id == resource_id)
        .order_by(ResourceComment.created_at.desc())
        .all()
    )
    # Add username to each comment
    for comment in comments:
        comment_user = db.get(User, comment.user_id)
        comment.username = comment_user.username if comment_user else "Unknown User"
    return comments


@router.post("/{resource_id}/rating", response_model=ResourceRead)
def rate_resource(resource_id: int, payload: RatingCreate, db: Session = Depends(db_session), user: User = Depends(get_current_user)):
    r = db.get(Resource, resource_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resource not found")

    existing = db.query(ResourceRating).filter(ResourceRating.user_id == user.id, ResourceRating.resource_id == resource_id).first()
    if existing:
        # Update aggregate removing old rating then adding new
        r.rating_sum = r.rating_sum - existing.rating + payload.rating
        existing.rating = payload.rating
        db.add(existing)
    else:
        rr = ResourceRating(user_id=user.id, resource_id=resource_id, rating=payload.rating)
        db.add(rr)
        r.rating_sum = r.rating_sum + payload.rating
        r.rating_count = r.rating_count + 1

    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.delete("/bulk", response_model=ResourcesBulkDeleteResponse)
def bulk_delete_resources(
    payload: ResourcesBulkDeleteRequest,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
):
    if not settings.API_KEY or x_api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    deleted = 0
    not_found: list[int] = []

    for rid in payload.ids:
        r = db.get(Resource, rid)
        if not r:
            not_found.append(rid)
            continue

        # Delete file only if this is the last DB entry pointing to it
        refs = db.query(Resource).filter(Resource.storage_path == r.storage_path, Resource.id != r.id).count()
        if refs == 0:
            try:
                get_storage().delete(r.storage_path)
            except Exception:
                pass

        db.delete(r)
        deleted += 1

    db.commit()
    return ResourcesBulkDeleteResponse(deleted=deleted, not_found=not_found)


@router.post("/{resource_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
def add_bookmark(resource_id: int, db: Session = Depends(db_session), user: User = Depends(get_current_user)):
    r = db.get(Resource, resource_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resource not found")
    if db.query(ResourceBookmark).filter(ResourceBookmark.user_id == user.id, ResourceBookmark.resource_id == resource_id).first():
        return
    bm = ResourceBookmark(user_id=user.id, resource_id=resource_id)
    db.add(bm)
    db.commit()
    return


@router.delete("/{resource_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
def remove_bookmark(resource_id: int, db: Session = Depends(db_session), user: User = Depends(get_current_user)):
    bm = db.query(ResourceBookmark).filter(ResourceBookmark.user_id == user.id, ResourceBookmark.resource_id == resource_id).first()
    if not bm:
        return
    db.delete(bm)
    db.commit()
    return


@router.get("/bookmarks", response_model=list[ResourceRead])
def list_bookmarks(db: Session = Depends(db_session), user: User = Depends(get_current_user)):
    bms = (
        db.query(ResourceBookmark)
        .filter(ResourceBookmark.user_id == user.id)
        .all()
    )
    ids = [b.resource_id for b in bms]
    if not ids:
        return []
    resources = db.query(Resource).filter(Resource.id.in_(ids)).order_by(desc(Resource.created_at)).all()
    return resources
