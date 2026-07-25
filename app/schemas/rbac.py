"""RBAC API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PermissionOut(BaseModel):
    id: int
    code: str
    name: str
    description: str
    group_name: str

    model_config = {"from_attributes": True}


class RoleOut(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    is_system: bool
    permission_codes: list[str] = []

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=50, pattern=r"^[a-z0-9_\-]+$")
    description: str = ""
    permission_codes: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = None
    permission_codes: list[str] | None = None
