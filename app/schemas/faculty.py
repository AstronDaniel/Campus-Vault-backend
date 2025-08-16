from pydantic import BaseModel, Field


class FacultyBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=2, max_length=50)


class FacultyCreate(FacultyBase):
    pass


class FacultyRead(FacultyBase):
    id: int

    class Config:
        from_attributes = True
