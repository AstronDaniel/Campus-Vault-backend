from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# Enrollment model intentionally disabled as per current app scope (no per-course enrollments)
# Keeping the file for potential future use.
class Enrollment(Base):
    __tablename__ = "enrollments"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_unit_id: Mapped[int] = mapped_column(ForeignKey("course_units.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "course_unit_id", name="pk_enrollments"),
    )
