"""Pydantic-Modelle für Subscriptions."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SubscriptionStatus = Literal["trialing", "active", "past_due", "canceled"]


class SubscriptionRecord(BaseModel):
    """Persistiertes Abo pro Mandant."""

    account_id: str
    plan_id: str = "trial"
    status: SubscriptionStatus = "trialing"
    current_period_start: datetime
    current_period_end: datetime
    quota_window_start: datetime
    override_max_mails: int | None = None
    override_max_properties: int | None = None
    override_max_users: int | None = None
    stripe_customer_id: str = ""
    stripe_subscription_id: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())
