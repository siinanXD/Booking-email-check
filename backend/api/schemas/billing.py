"""Pydantic-Schemas für Billing-API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlanCatalogItem(BaseModel):
    plan_id: str
    display_name: str
    price_eur_monthly: int
    monthly_mail_quota: int
    max_properties: int
    max_users: int
    max_mailboxes: int
    features: list[str]


class PlanCatalogResponse(BaseModel):
    items: list[PlanCatalogItem]


class SubscriptionResponse(BaseModel):
    plan_id: str
    plan_name: str
    status: str
    period_end: str
    quota_window_start: str
    mails_used: int
    mails_limit: int
    properties_used: int
    properties_limit: int
    users_used: int
    users_limit: int
    mailboxes_limit: int
    effective_features: list[str]
    self_service: bool = False


class CheckoutRequest(BaseModel):
    plan_id: str


class CheckoutResponse(BaseModel):
    url: str


class PortalResponse(BaseModel):
    url: str


class AdminSubscriptionSetRequest(BaseModel):
    plan_id: str
    period_end: str | None = None


class AdminSubscriptionExtendTrialRequest(BaseModel):
    days: int = Field(ge=1, le=365)


class AdminSubscriptionOverridesRequest(BaseModel):
    override_max_mails: int | None = None
    override_max_properties: int | None = None
    override_max_users: int | None = None
