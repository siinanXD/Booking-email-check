"""Zentrale Entitlement- und Quota-Logik."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from backend.core.config.settings import Settings
from backend.features.billing.access import trial_expired
from backend.features.billing.plans import (
    PlanDefinition,
    get_plan,
    is_unlimited,
)
from backend.infrastructure.repositories._subscription_models import SubscriptionRecord
from backend.infrastructure.repositories.account_repository import AccountRepository
from backend.infrastructure.repositories.mail_metrics_repository import (
    MailMetricsRepository,
)
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRepository,
)
from backend.infrastructure.repositories.property_repository import PropertyRepository
from backend.infrastructure.repositories.subscription_repository import (
    SubscriptionRepository,
)
from backend.infrastructure.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class QuotaStatus:
    """Mail-Quota-Status für einen Mandanten."""

    used: int
    limit: int
    exhausted: bool


class EntitlementService:
    """Prüft Pläne, Features und Nutzungslimits."""

    def __init__(
        self,
        settings: Settings,
        subscription_repo: SubscriptionRepository,
        mail_metrics_repo: MailMetricsRepository,
        account_repo: AccountRepository,
        user_repo: UserRepository,
        property_repo: PropertyRepository,
        platform_settings_repo: PlatformSettingsRepository,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._settings = settings
        self._subscription_repo = subscription_repo
        self._mail_metrics_repo = mail_metrics_repo
        self._account_repo = account_repo
        self._user_repo = user_repo
        self._property_repo = property_repo
        self._platform_settings_repo = platform_settings_repo

    @property
    def enforcement_enabled(self) -> bool:
        return self._settings.billing_enforcement_enabled

    def plan_for(self, account_id: str) -> PlanDefinition:
        """Effektiver Plan; ohne Abo oder canceled → Trial-Fallback."""
        sub = self._subscription_repo.get_by_account(account_id)
        if sub is None or sub.status == "canceled":
            return get_plan("trial")
        return get_plan(sub.plan_id)

    def effective_features(self, account_id: str) -> set[str]:
        """Plan-Features ∪ manuelle Admin-Toggles."""
        plan = self.plan_for(account_id)
        features = set(plan.features)
        platform = self._platform_settings_repo.get(account_id)
        if platform is not None:
            for name, enabled in platform.features.items():
                if enabled:
                    features.add(name)
        return features

    def _effective_limit(
        self,
        account_id: str,
        plan_value: int,
        override: int | None,
    ) -> int:
        if override is not None:
            return override
        return plan_value

    def _rolled_subscription(self, account_id: str) -> SubscriptionRecord | None:
        now = datetime.now(UTC)
        return self._subscription_repo.roll_quota_window(account_id, now)

    def mail_quota(self, account_id: str) -> QuotaStatus:
        """Zählt verarbeitete Mails im aktuellen Quota-Fenster."""
        plan = self.plan_for(account_id)
        sub = self._rolled_subscription(account_id)
        limit = self._effective_limit(
            account_id,
            plan.monthly_mail_quota,
            sub.override_max_mails if sub else None,
        )
        if not self.enforcement_enabled or is_unlimited(limit):
            return QuotaStatus(used=0, limit=limit, exhausted=False)

        now = datetime.now(UTC)
        window_start = sub.quota_window_start if sub else now
        account = self._account_repo.get_by_id(account_id)
        exclude_before = account.mail_initial_sync_completed_at if account else None
        used = self._mail_metrics_repo.count_between(
            window_start,
            now,
            account_id=account_id,
            exclude_processed_before=exclude_before,
        )
        exhausted = used >= limit or trial_expired(sub)
        return QuotaStatus(used=used, limit=limit, exhausted=exhausted)

    def can_create_property(self, account_id: str) -> bool:
        """True wenn eine weitere Unterkunft angelegt werden darf."""
        if not self.enforcement_enabled:
            return True
        plan = self.plan_for(account_id)
        sub = self._subscription_repo.get_by_account(account_id)
        limit = self._effective_limit(
            account_id,
            plan.max_properties,
            sub.override_max_properties if sub else None,
        )
        if is_unlimited(limit):
            return True
        return self._property_repo.count_for_account(account_id) < limit

    def can_create_user(self, account_id: str) -> bool:
        """True wenn ein weiterer Nutzer angelegt werden darf."""
        if not self.enforcement_enabled:
            return True
        plan = self.plan_for(account_id)
        sub = self._subscription_repo.get_by_account(account_id)
        limit = self._effective_limit(
            account_id,
            plan.max_users,
            sub.override_max_users if sub else None,
        )
        if is_unlimited(limit):
            return True
        return self._user_repo.count_for_account(account_id) < limit

    def usage_snapshot(self, account_id: str) -> dict[str, int]:
        """Aktuelle Nutzungszähler für API-Antworten."""
        quota = self.mail_quota(account_id)
        plan = self.plan_for(account_id)
        sub = self._subscription_repo.get_by_account(account_id)
        props_limit = self._effective_limit(
            account_id,
            plan.max_properties,
            sub.override_max_properties if sub else None,
        )
        users_limit = self._effective_limit(
            account_id,
            plan.max_users,
            sub.override_max_users if sub else None,
        )
        mailboxes_limit = plan.max_mailboxes
        return {
            "mails_used": quota.used,
            "mails_limit": quota.limit,
            "properties_used": self._property_repo.count_for_account(account_id),
            "properties_limit": props_limit,
            "users_used": self._user_repo.count_for_account(account_id),
            "users_limit": users_limit,
            "mailboxes_limit": mailboxes_limit,
        }
