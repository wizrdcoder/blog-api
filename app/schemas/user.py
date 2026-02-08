from typing import Optional
from datetime import datetime
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ValidationInfo,
    field_validator,
    ConfigDict,
)
import re
from enum import Enum


class UserRole(str, Enum):
    User = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)

    @field_validator("username")
    def username_alphanumeric(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username must be alphanumeric with underscore only")
        return v


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def password_match(cls, v, info: ValidationInfo):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Password do not match")
        return v


class UserUpdate(UserBase):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    boi: Optional[str] = None
    avatar_url: Optional[str] = None
    website: Optional[str] = None

    model_config = ConfigDict(extra="forbid")  # prevents extra fields


class UserInDBBase(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    is_superuser: bool
    role: UserRole
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class User(UserInDBBase):
    pass


class UserWithProfile(User):
    boi: Optional[str] = None
    avatar_url: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None


class UserWithStats(User):
    post_count: int = 0
    comment_count: int = 0


class UsersPaginated(BaseModel):
    items: list[User]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)
