from sqlalchemy import Integer, String, SmallInteger, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CourseUnit(Base):
    __tablename__ = "course_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    __table_args__ = (
        CheckConstraint("year >= 1", name="ck_course_unit_year_positive"),
        CheckConstraint("semester in (1, 2)", name="ck_course_unit_semester_1_2"),
    )
