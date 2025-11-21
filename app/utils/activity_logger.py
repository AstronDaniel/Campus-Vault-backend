from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.services.activity_service import ActivityService
from app.models.activity import ActivityType

class ActivityLogger:
    @staticmethod
    def log_user_login(db: Session, user_id: int, details: Optional[Dict[str, Any]] = None):
        return ActivityService.log_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.user_login,
            description="User logged in",
            details=details
        )
    
    @staticmethod
    def log_user_logout(db: Session, user_id: int, details: Optional[Dict[str, Any]] = None):
        return ActivityService.log_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.user_logout,
            description="User logged out",
            details=details
        )
    
    @staticmethod
    def log_resource_upload(db: Session, user_id: int, resource_name: str, details: Optional[Dict[str, Any]] = None):
        return ActivityService.log_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.resource_uploaded,
            description=f"Uploaded resource: {resource_name}",
            details=details
        )
    
    @staticmethod
    def log_resource_download(db: Session, user_id: int, resource_name: str, details: Optional[Dict[str, Any]] = None):
        return ActivityService.log_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.resource_downloaded,
            description=f"Downloaded resource: {resource_name}",
            details=details
        )
    
    @staticmethod
    def log_user_registration(db: Session, user_id: int, details: Optional[Dict[str, Any]] = None):
        return ActivityService.log_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.user_registered,
            description="New user registered",
            details=details
        )
