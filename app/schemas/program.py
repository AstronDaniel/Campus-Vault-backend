from pydantic import BaseModel, Field
from typing import Optional


class ProgramCreate(BaseModel):
    faculty_id: int
    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=2, max_length=50)


class ProgramRead(BaseModel):
    id: int
    faculty_id: int
    name: str
    code: str

    class Config:
        from_attributes = True


class ProgramUpdate(BaseModel):
    faculty_id: Optional[int] = None
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, min_length=2, max_length=50)
