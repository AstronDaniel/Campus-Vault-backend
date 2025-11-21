from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base

class ActivityType(str, enum.Enum):
    user_login = "user_login"
    user_logout = "user_logout"
    user_registered = "user_registered"
    resource_uploaded = "resource_uploaded"
    resource_downloaded = "resource_downloaded"
    resource_deleted = "resource_deleted"
    course_created = "course_created"
    course_updated = "course_updated"
    course_deleted = "course_deleted"
    faculty_created = "faculty_created"
    faculty_updated = "faculty_updated"
    program_created = "program_created"
    program_updated = "program_updated"
    user_role_changed = "user_role_changed"

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
