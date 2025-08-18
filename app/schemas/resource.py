from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ResourceBase(BaseModel):
    course_unit_id: int
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)


class ResourceCreate(ResourceBase):
    # For metadata-only creation (actual file via upload endpoint)
    filename: str
    content_type: str
    size_bytes: int
    sha256: str


class ResourceRead(ResourceBase):
    id: int
    uploader_id: int
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    storage_path: str
    url: str
    download_count: int
    last_download_at: Optional[datetime] = None
    rating_sum: int
    rating_count: int
    created_at: datetime

    class Config:
        from_attributes = True

    @property
    def rating_avg(self) -> float:
        if self.rating_count:
            return round(self.rating_sum / self.rating_count, 2)
        return 0.0


class ResourceListResponse(BaseModel):
    items: list[ResourceRead]
    total: int
    limit: int
    offset: int


class ResourceDuplicateInfo(BaseModel):
    duplicate: bool
    existing: Optional[ResourceRead] = None


class ResourceUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)


class ResourceLinkRequest(BaseModel):
    course_unit_id: int
    title: Optional[str] = None
    description: Optional[str] = None


class ResourcesBulkDeleteRequest(BaseModel):
    ids: list[int]


class ResourcesBulkDeleteResponse(BaseModel):
    deleted: int
    not_found: list[int] = []


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class CommentRead(BaseModel):
    id: int
    resource_id: int
    user_id: int
    body: str
    created_at: datetime

    class Config:
        from_attributes = True


class RatingCreate(BaseModel):
    rating: int

    @field_validator("rating")
    @classmethod
    def valid_rating(cls, v: int):
        if v < 1 or v > 5:
            raise ValueError("rating must be between 1 and 5")
        return v
