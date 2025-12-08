from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, BigInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (
        UniqueConstraint("course_unit_id", "sha256", name="uq_resource_courseunit_sha256"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    course_unit_id: Mapped[int] = mapped_column(ForeignKey("course_units.id", ondelete="CASCADE"), index=True, nullable=False)
    uploader_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True, default="notes")  # 'notes', 'past_paper', 'assignment', etc.

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)

    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_download_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # rating aggregates
    rating_sum: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    course_unit = relationship("CourseUnit", lazy="joined")
