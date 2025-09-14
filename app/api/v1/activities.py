from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.services.activity_service import ActivityService
from app.models.activity import ActivityType
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/v1/activities", tags=["activities"])

class ActivityResponse(BaseModel):
    id: int
    user_id: int
    activity_type: ActivityType
    description: str
    details: Optional[str] = None
    created_at: datetime
    user_name: Optional[str] = None
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[ActivityResponse])
async def get_activities(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    limit: int = Query(50, ge=1, le=100, description="Number of activities to return"),
    offset: int = Query(0, ge=0, description="Number of activities to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get activity feed with optional filtering"""
    activities = ActivityService.get_activities(db, user_id=user_id, limit=limit, offset=offset)
    
    # Add user names to response
    response_activities = []
    for activity in activities:
        activity_dict = {
            "id": activity.id,
            "user_id": activity.user_id,
            "activity_type": activity.activity_type,
            "description": activity.description,
            "details": activity.details,
            "created_at": activity.created_at,
            "user_name": activity.user.username if activity.user else None
        }
        response_activities.append(ActivityResponse(**activity_dict))
    
    return response_activities

@router.get("/me", response_model=List[ActivityResponse])
async def get_my_activities(
    limit: int = Query(50, ge=1, le=100, description="Number of activities to return"),
    offset: int = Query(0, ge=0, description="Number of activities to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's activities"""
    activities = ActivityService.get_activities(db, user_id=current_user.id, limit=limit, offset=offset)
    
    response_activities = []
    for activity in activities:
        activity_dict = {
            "id": activity.id,
            "user_id": activity.user_id,
            "activity_type": activity.activity_type,
            "description": activity.description,
            "details": activity.details,
            "created_at": activity.created_at,
            "user_name": current_user.username
        }
        response_activities.append(ActivityResponse(**activity_dict))
    
    return response_activities

@router.get("/types", response_model=List[str])
async def get_activity_types():
    """Get all available activity types"""
    return [activity_type.value for activity_type in ActivityType]
async def get_activity_types():
    """Get all available activity types"""
    return [activity_type.value for activity_type in ActivityType]

@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific activity by ID"""
    activity = ActivityService.get_activity_by_id(db, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    activity_dict = {
        "id": activity.id,
        "user_id": activity.user_id,
        "activity_type": activity.activity_type,
        "description": activity.description,
        "details": activity.details,
        "created_at": activity.created_at,
        "user_name": activity.user.username if activity.user else None
    }
    
    return ActivityResponse(**activity_dict)
