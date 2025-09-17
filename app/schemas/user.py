from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    faculty_id: int
    program_id: int


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    # Note: role is NOT included here - it defaults to STUDENT


class UserRead(UserBase):
    id: int
    avatar_url: Optional[str] = None
    is_verified: bool
    created_at: datetime
    role: UserRole  # This shows the role in responses

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    # Partial update for profile fields (email and username optional)
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    faculty_id: Optional[int] = None
    program_id: Optional[int] = None
    avatar_url: Optional[str] = None
    role: Optional[UserRole] = None
    # Note: role is NOT included here for regular users


class PasswordUpdate(BaseModel):
    old_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class AdminPasswordReset(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class UsersBulkDeleteRequest(BaseModel):
    ids: list[int]


class UsersBulkDeleteResponse(BaseModel):
    deleted: int
    not_found: list[int] = []


class AdminVerifyUserRequest(BaseModel):
    is_verified: bool


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    faculty_id: int
    program_id: int
    avatar_url: Optional[str] = None
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserAdminUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    faculty_id: Optional[int] = None
    program_id: Optional[int] = None
    is_verified: Optional[bool] = None
