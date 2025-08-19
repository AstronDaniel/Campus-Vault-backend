from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4000)


class NotificationRead(BaseModel):
    id: int
    user_id: int
    title: str
    body: str
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationBroadcast(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4000)
