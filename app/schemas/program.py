from pydantic import BaseModel, Field
from typing import Optional

class ProgramBase(BaseModel):
    name: str
    code: str
    faculty_id: int
    duration_years: int = Field(default=4, ge=1, le=6, description="Program duration in years (1–6)")

class ProgramCreate(ProgramBase):
    pass

class ProgramUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    faculty_id: Optional[int] = None
    duration_years: Optional[int] = Field(default=None, ge=1, le=6)

class ProgramRead(BaseModel):
    id: int
    name: str
    code: str
    faculty_id: int
    duration_years: int