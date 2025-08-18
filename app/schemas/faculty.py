from pydantic import BaseModel, Field
from typing import Optional


class FacultyBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=2, max_length=50)


class FacultyCreate(FacultyBase):
    pass


class FacultyRead(FacultyBase):
    id: int

    class Config:
        from_attributes = True


class FacultyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, min_length=2, max_length=50)
