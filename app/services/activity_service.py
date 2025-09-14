from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
import json
from app.models.activity import Activity, ActivityType
from app.models.user import User

class ActivityService:
    @staticmethod
    def log_activity(
        db: Session, 
        user_id: int, 
        activity_type: ActivityType, 
        description: str, 
        details: Optional[dict] = None
    ) -> Activity:
        """Log an activity to the database"""
        activity = Activity(
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            details=json.dumps(details) if details else None
        )
        db.add(activity)
        db.commit()
        db.refresh(activity)
        return activity
    
    @staticmethod
    def get_activities(
        db: Session, 
        user_id: Optional[int] = None, 
        activity_type: Optional[ActivityType] = None,
        limit: int = 50, 
        offset: int = 0
    ) -> List[Activity]:
        """Get activities with optional filtering"""
        query = db.query(Activity).join(User)
        
        if user_id:
            query = query.filter(Activity.user_id == user_id)
            
        if activity_type:
            query = query.filter(Activity.activity_type == activity_type)
        
        return query.order_by(desc(Activity.created_at))\
                   .offset(offset)\
                   .limit(limit)\
                   .all()
    
    @staticmethod
    def get_activity_by_id(db: Session, activity_id: int) -> Optional[Activity]:
        """Get a specific activity by ID"""
        return db.query(Activity).filter(Activity.id == activity_id).first()

  