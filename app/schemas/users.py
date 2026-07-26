"""User schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.enums import UserRole, UserStatus
from app.schemas.auth import UserPublic


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role_id: int | None = None
    role: UserRole | None = UserRole.member
    send_credentials: bool = False

    @model_validator(mode="after")
    def password_or_send_credentials(self):
        if self.send_credentials:
            return self
        if not self.password or len(self.password) < 8:
            raise ValueError(
                "Password obrigatoria (min. 8) quando nao envia credenciais por email."
            )
        return self


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    role_id: int | None = None
    role: UserRole | None = None
    status: UserStatus | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    send_credentials: bool = False


class UserListResponse(BaseModel):
    users: list[UserPublic]
