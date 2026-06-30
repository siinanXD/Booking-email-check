"""Account-Admin-DTOs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AccountListItem(BaseModel):
    """Account-Metadaten für Admin-Listen."""

    id: str
    display_name: str
    contact_email: str
    account_type: str
    company_name: str | None = None
    phone: str | None = None
    status: str
    rejection_reason: str | None = None
    created_at: str


class AccountListResponse(BaseModel):
    """Liste von Accounts."""

    items: list[AccountListItem]
    total: int


class AccountRejectRequest(BaseModel):
    """Optionaler Ablehnungsgrund."""

    reason: str | None = Field(default=None, max_length=500)


class AccountActionResponse(BaseModel):
    """Ergebnis Freischalten/Ablehnen."""

    id: str
    status: str
    message: str


class AdminMeResponse(BaseModel):
    """Plattform-Admin-Kontext."""

    id: str
    email: str
    role: str
    account_id: str | None = None
    mail_onboarding_required: bool = False


class AccountExpiryRequest(BaseModel):
    """Setzt ein Ablaufdatum (ISO-8601) oder None zum Entfernen."""

    expires_at: str | None = Field(default=None)


class UserLockRequest(BaseModel):
    """Sperrt oder entsperrt einen User."""

    locked: bool


class UserResetPasswordRequest(BaseModel):
    """Neues Passwort vom Admin."""

    new_password: str = Field(min_length=8, max_length=128)


class AccountFeatureRequest(BaseModel):
    """Schaltet ein Zusatz-Feature für einen Account (Plattform-Admin)."""

    feature: str = Field(min_length=1)
    enabled: bool


class AccountFeatureResponse(BaseModel):
    """Neuer Feature-Stand inkl. ggf. erzeugter Backfill-Aufträge."""

    features: dict[str, bool] = Field(default_factory=dict)
    backfilled: int = 0
