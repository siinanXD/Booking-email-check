"""Verdrahtung des EntitlementService."""

from __future__ import annotations

from backend.core.config.settings import Settings
from backend.features.billing.entitlement_service import EntitlementService
from backend.infrastructure.repositories.account_repository import AccountRepository
from backend.infrastructure.repositories.mail_metrics_repository import (
    MailMetricsRepository,
)
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRepository,
)
from backend.infrastructure.repositories.property_repository import PropertyRepository
from backend.infrastructure.repositories.subscription_repository import (
    SubscriptionRepository,
)
from backend.infrastructure.repositories.user_repository import UserRepository


def build_entitlement_service(
    settings: Settings,
    db: Db,
    subscription_repo: SubscriptionRepository,
    metrics_repo: MailMetricsRepository,
    account_repo: AccountRepository,
    user_repo: UserRepository,
    platform_settings_repo: PlatformSettingsRepository,
) -> EntitlementService:
    """Erzeugt den zentralen EntitlementService."""
    property_repo = PropertyRepository(db)
    return EntitlementService(
        settings,
        subscription_repo,
        metrics_repo,
        account_repo,
        user_repo,
        property_repo,
        platform_settings_repo,
    )
