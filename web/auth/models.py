"""Auth-DTOs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login-Body."""

    email: str = Field(min_length=3)
    password: str


class TokenResponse(BaseModel):
    """JWT-Antwort."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Öffentliches Benutzerprofil."""

    id: str
    email: str
    role: str
