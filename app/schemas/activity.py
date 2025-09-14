from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.activity import ActivityType

class ActivityBase(BaseModel):
    activity_type: ActivityType
    description: str
    details: Optional[str] = None

class ActivityCreate(ActivityBase):
    user_id: int

class ActivityResponse(ActivityBase):
    id: int
    user_id: int
    created_at: datetime
    user_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class ActivityFilter(BaseModel):
    user_id: Optional[int] = None
    activity_type: Optional[ActivityType] = None
    limit: int = 50
    offset: int = 0
