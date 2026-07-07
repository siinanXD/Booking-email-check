"""Fest codierter Plan-Katalog (keine Env-Vars)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from backend.core.config.settings import Settings

UNLIMITED = -1

PlanId = Literal["trial", "standard", "pro", "business", "legacy"]

FEATURE_WHATSAPP = "whatsapp"
FEATURE_AUTO_APPROVE = "auto_approve"
FEATURE_CLEANING_SCHEDULE = "cleaning_schedule"

ALL_PLAN_FEATURES = frozenset(
    {FEATURE_WHATSAPP, FEATURE_AUTO_APPROVE, FEATURE_CLEANING_SCHEDULE}
)

PUBLIC_PLAN_IDS: tuple[PlanId, ...] = ("trial", "standard", "pro", "business")


class PlanDefinition(BaseModel):
    """Definition eines Abo-Plans."""

    plan_id: PlanId
    display_name: str
    price_eur_monthly: int
    monthly_mail_quota: int
    max_properties: int
    max_users: int
    max_mailboxes: int
    features: frozenset[str] = Field(default_factory=frozenset)


PLANS: dict[PlanId, PlanDefinition] = {
    "trial": PlanDefinition(
        plan_id="trial",
        display_name="Trial",
        price_eur_monthly=0,
        monthly_mail_quota=50,
        max_properties=1,
        max_users=1,
        max_mailboxes=1,
        features=frozenset(),
    ),
    "standard": PlanDefinition(
        plan_id="standard",
        display_name="Standard",
        price_eur_monthly=50,
        monthly_mail_quota=500,
        max_properties=3,
        max_users=2,
        max_mailboxes=1,
        features=frozenset({FEATURE_WHATSAPP}),
    ),
    "pro": PlanDefinition(
        plan_id="pro",
        display_name="Pro",
        price_eur_monthly=130,
        monthly_mail_quota=2000,
        max_properties=15,
        max_users=5,
        max_mailboxes=3,
        features=frozenset(
            {FEATURE_WHATSAPP, FEATURE_AUTO_APPROVE, FEATURE_CLEANING_SCHEDULE}
        ),
    ),
    "business": PlanDefinition(
        plan_id="business",
        display_name="Business",
        price_eur_monthly=450,
        monthly_mail_quota=10000,
        max_properties=UNLIMITED,
        max_users=UNLIMITED,
        max_mailboxes=10,
        features=frozenset(
            {FEATURE_WHATSAPP, FEATURE_AUTO_APPROVE, FEATURE_CLEANING_SCHEDULE}
        ),
    ),
    "legacy": PlanDefinition(
        plan_id="legacy",
        display_name="Legacy (intern)",
        price_eur_monthly=0,
        monthly_mail_quota=UNLIMITED,
        max_properties=UNLIMITED,
        max_users=UNLIMITED,
        max_mailboxes=UNLIMITED,
        features=ALL_PLAN_FEATURES,
    ),
}

TRIAL_DAYS = 14


def get_plan(plan_id: str) -> PlanDefinition:
    """Lädt Plan-Definition; unbekannte IDs → Trial."""
    if plan_id in PLANS:
        return PLANS[plan_id]  # type: ignore[index]
    return PLANS["trial"]


def public_plans() -> list[PlanDefinition]:
    """Öffentlicher Katalog ohne Legacy."""
    return [PLANS[pid] for pid in PUBLIC_PLAN_IDS]


def is_unlimited(value: int) -> bool:
    """True wenn Limit unbegrenzt."""
    return value == UNLIMITED


CHECKOUT_PLAN_IDS: tuple[PlanId, ...] = ("standard", "pro", "business")


def stripe_price_map(settings: Settings) -> dict[str, str]:
    """Plan-ID → Stripe Price-ID aus Settings."""
    return {
        "standard": settings.stripe_price_standard.strip(),
        "pro": settings.stripe_price_pro.strip(),
        "business": settings.stripe_price_business.strip(),
    }


def price_id_for_plan(settings: Settings, plan_id: str) -> str | None:
    """Stripe Price-ID für einen Plan; None wenn nicht konfiguriert."""
    price_id = stripe_price_map(settings).get(plan_id, "").strip()
    return price_id or None


def plan_id_for_price(settings: Settings, price_id: str) -> str | None:
    """Plan-ID aus Stripe Price-ID (Webhook-Reverse-Lookup)."""
    needle = price_id.strip()
    if not needle:
        return None
    for plan_id, configured in stripe_price_map(settings).items():
        if configured == needle:
            return plan_id
    return None
