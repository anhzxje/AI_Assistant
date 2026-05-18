"""Schemas for local authentication APIs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class UserPublic(BaseModel):
    user_id: str
    email: str
    display_name: str
    role: str
    role_label: str
    disabled: bool = False


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class LogoutResponse(BaseModel):
    ok: bool = True


class MeResponse(BaseModel):
    authenticated: bool
    user: UserPublic | None = None


class GoogleLoginStatusResponse(BaseModel):
    configured: bool
    scopes: list[str]
    redirect_uri: str
    message: str
