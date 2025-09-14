from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User, UserRole
from app.models.resource import Resource
from app.models.resource_download import ResourceDownloadEvent
from app.services.user_service import UserService
from app.api.deps import db_session, get_current_user
from app.core.config import get_settings
from app.services.activity_service import ActivityService
from app.models.activity import ActivityType

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
settings = get_settings()


def _require_api_key(x_api_key: str | None) -> None:
    if not settings.API_KEY or x_api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")


@router.get("/stats")
def stats(x_api_key: str | None = Header(None, alias="X-API-Key"), db: Session = Depends(db_session)):
    _require_api_key(x_api_key)

    users = db.query(func.count(User.id)).scalar() or 0
    resources = db.query(func.count(Resource.id)).scalar() or 0
    downloads = db.query(func.count(ResourceDownloadEvent.id)).scalar() or 0

    return {
        "users": users,
        "resources": resources,
        "downloads": downloads,
    }


@router.get("/downloads/daily")
def downloads_daily(
    days: int = 7,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    db: Session = Depends(db_session),
):
    _require_api_key(x_api_key)

    since = datetime.utcnow() - timedelta(days=max(1, min(days, 90)))

    rows = (
        db.query(
            func.date(ResourceDownloadEvent.created_at).label("day"),
            func.count(ResourceDownloadEvent.id),
        )
        .filter(ResourceDownloadEvent.created_at >= since)
        .group_by(func.date(ResourceDownloadEvent.created_at))
        .order_by(func.date(ResourceDownloadEvent.created_at))
        .all()
    )
    return [{"day": str(day), "count": count} for day, count in rows]


class RoleUpdateRequest(BaseModel):
    role: UserRole


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    faculty_id: int
    program_id: int
    is_verified: bool

    class Config:
        from_attributes = True


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_update: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin only: Update user role"""
    # Check if current user is admin
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get user info before update for logging
    target_user = UserService.get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_role = target_user.role
    
    # Update the role
    updated_user = UserService.update_user_role(db, user_id, role_update.role)
    
    # Log the role change activity
    ActivityService.log_activity(
        db=db,
        user_id=current_user.id,
        activity_type=ActivityType.USER_ROLE_CHANGED,
        description=f"Changed user {target_user.username} role from {old_role.value} to {role_update.role.value}",
        details={
            "target_user_id": user_id,
            "target_username": target_user.username,
            "old_role": old_role.value,
            "new_role": role_update.role.value
        }
    )
    
    return {"message": f"User role updated to {role_update.role.value}", "user_id": user_id}


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin only: Get all users"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    users = UserService.get_all_users(db, skip=skip, limit=limit)
    return users
