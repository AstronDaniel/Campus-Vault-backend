from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base

class ActivityType(enum.Enum):
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTERED = "user_registered"
    RESOURCE_UPLOADED = "resource_uploaded"
    RESOURCE_DOWNLOADED = "resource_downloaded"
    RESOURCE_DELETED = "resource_deleted"
    COURSE_CREATED = "course_created"
    COURSE_UPDATED = "course_updated"
    COURSE_DELETED = "course_deleted"
    FACULTY_CREATED = "faculty_created"
    FACULTY_UPDATED = "faculty_updated"
    PROGRAM_CREATED = "program_created"
    PROGRAM_UPDATED = "program_updated"
    USER_ROLE_CHANGED = "user_role_changed"

class Activity(Base):
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_type = Column(Enum(ActivityType), nullable=False)
    description = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="activities")
