"""Auth / user API schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole, UserStatus


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserPublic(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
    status: UserStatus
    role_id: int | None = None
    perfil_nome: str | None = None
    profile_image_key: str | None = None
    permissions: list[str] = []

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    user: UserPublic


class MeResponse(BaseModel):
    user: UserPublic


class MessageResponse(BaseModel):
    message: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)
