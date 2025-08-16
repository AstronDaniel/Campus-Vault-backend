from pydantic import BaseModel, Field, field_validator


class CourseUnitCreate(BaseModel):
    program_id: int
    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    year: int = Field(ge=1)
    semester: int

    @field_validator("semester")
    @classmethod
    def validate_semester(cls, v):
        if v not in (1, 2):
            raise ValueError("semester must be 1 or 2")
        return v


class CourseUnitRead(BaseModel):
    id: int
    program_id: int
    name: str
    code: str
    year: int
    semester: int

    class Config:
        from_attributes = True
