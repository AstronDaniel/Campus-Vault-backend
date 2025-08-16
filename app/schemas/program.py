from pydantic import BaseModel, Field


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
