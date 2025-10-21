from sqlalchemy import Integer, String, ForeignKey, Column, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculties.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    duration_years = Column(Integer, nullable=False, default=4)

    __table_args__ = (
        CheckConstraint("duration_years >= 1 AND duration_years <= 6", name="ck_programs_duration_range"),
    )
