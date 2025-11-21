from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base

if TYPE_CHECKING:
    from app.models.activity import Activity


class UserRole(enum.Enum):
    student = "student"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculties.id", ondelete="RESTRICT"), index=True, nullable=False)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="RESTRICT"), index=True, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.student, nullable=False, server_default="student")

    # Relationships
    activities: Mapped[list["Activity"]] = relationship("Activity", back_populates="user")
