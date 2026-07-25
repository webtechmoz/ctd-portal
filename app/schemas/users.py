"""User schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole, UserStatus
from app.schemas.auth import UserPublic


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role_id: int | None = None
    role: UserRole | None = UserRole.member


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    role_id: int | None = None
    role: UserRole | None = None
    status: UserStatus | None = None


class UserListResponse(BaseModel):
    users: list[UserPublic]
