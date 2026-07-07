"""Billing-Verdrahtung für build_app_context."""

from __future__ import annotations

from backend.core.config.settings import Settings
from backend.features.billing.entitlement_service import EntitlementService
from backend.features.billing.stripe_service import StripeService
from backend.features.billing.stripe_webhook import StripeWebhookHandler
from backend.features.billing.wiring import build_entitlement_service
from backend.infrastructure.repositories.account_repository import AccountRepository
from backend.infrastructure.repositories.mail_metrics_repository import (
    MailMetricsRepository,
)
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRepository,
)
from backend.infrastructure.repositories.subscription_repository import (
    SubscriptionRepository,
)
from backend.infrastructure.repositories.user_repository import UserRepository


def build_subscription_stack(
    cfg: Settings,
    db: Db,
    metrics_repo: MailMetricsRepository,
    account_repo: AccountRepository,
    user_repo: UserRepository,
    platform_settings_repo: PlatformSettingsRepository,
) -> tuple[
    SubscriptionRepository,
    EntitlementService,
    StripeService | None,
    StripeWebhookHandler | None,
]:
    """Subscription-Repo, EntitlementService und optional Stripe."""
    subscription_repo = SubscriptionRepository(db)
    entitlement_service = build_entitlement_service(
        cfg,
        db,
        subscription_repo,
        metrics_repo,
        account_repo,
        user_repo,
        platform_settings_repo,
    )
    stripe_service: StripeService | None = None
    stripe_webhook_handler: StripeWebhookHandler | None = None
    if cfg.stripe_enabled and cfg.stripe_secret_key.strip():
        stripe_service = StripeService(
            cfg,
            subscription_repo,
            account_repo,
            user_repo,
        )
        stripe_webhook_handler = StripeWebhookHandler(
            cfg,
            subscription_repo,
            stripe_service,
        )
    return (
        subscription_repo,
        entitlement_service,
        stripe_service,
        stripe_webhook_handler,
    )
