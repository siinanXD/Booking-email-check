"""Auth-DTOs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


def _empty_features() -> dict[str, bool]:
    return {}


class LoginRequest(BaseModel):
    """Login-Body."""

    email: str = Field(min_length=3)
    password: str


class RegisterRequest(BaseModel):
    """Registrierungs-Body."""

    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    password_confirm: str = Field(min_length=8)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=3, max_length=30)
    account_type: Literal["private", "business"] = "private"
    company_name: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def validate_registration(self) -> RegisterRequest:
        if self.password != self.password_confirm:
            msg = "Passwörter stimmen nicht überein"
            raise ValueError(msg)
        if self.account_type == "business" and not (self.company_name or "").strip():
            msg = "Firmenname ist bei gewerblicher Nutzung erforderlich"
            raise ValueError(msg)
        return self


class TokenResponse(BaseModel):
    """JWT-Antwort."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    """Antwort nach erfolgreicher Registrierung (ohne Login)."""

    message: str
    account_id: str
    status: str = "pending"


class UserResponse(BaseModel):
    """Öffentliches Benutzerprofil."""

    id: str
    email: str
    role: str
    account_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    account_status: str | None = None
    account_display_name: str | None = None
    mail_connection_status: str | None = None
    mail_onboarding_completed: bool | None = None
    # Pro Account freigeschaltete Zusatz-Features (z. B. cleaning_schedule).
    features: dict[str, bool] = Field(default_factory=_empty_features)
