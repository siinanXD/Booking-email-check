"""Billing: EntitlementService, Backfill, Enforcement."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.core.config.settings import Settings
from backend.core.models.entities import Property
from backend.features.billing.entitlement_service import EntitlementService
from backend.features.booking.entity_sync import _property_id
from backend.infrastructure.repositories.account_repository import AccountRepository
from backend.infrastructure.repositories.mail_metrics_repository import (
    MailMetricsRepository,
)
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRecord,
    PlatformSettingsRepository,
)
from backend.infrastructure.repositories.property_repository import PropertyRepository
from backend.infrastructure.repositories.subscription_repository import (
    SubscriptionRepository,
)
from backend.infrastructure.repositories.user_repository import UserRepository


def _settings(*, enforcement: bool = False) -> Settings:
    return Settings.model_validate(
        {
            "OPENAI_API_KEY": "sk-test",
            "MONGODB_URI": "mongodb://localhost",
            "LANGFUSE_PUBLIC_KEY": "pk",
            "LANGFUSE_SECRET_KEY": "sk",
            "BILLING_ENFORCEMENT_ENABLED": str(enforcement).lower(),
            "LLM_MODE": "mock",
        }
    )


def _service(mock_db: object, *, enforcement: bool = False) -> EntitlementService:
    from backend.core.utils.field_crypto import FieldCipher

    db = mock_db
    cipher = FieldCipher("")
    return EntitlementService(
        _settings(enforcement=enforcement),
        SubscriptionRepository(db),
        MailMetricsRepository(db),
        AccountRepository(db),
        UserRepository(db),
        PropertyRepository(db),
        PlatformSettingsRepository(db, cipher),
    )


def test_enforcement_disabled_allows_without_subscription(mock_db: object) -> None:
    svc = _service(mock_db, enforcement=False)
    account = AccountRepository(mock_db).create(
        display_name="A",
        contact_email="a@test.local",
        status="active",
    )
    assert svc.can_create_property(account.id)
    assert not svc.mail_quota(account.id).exhausted


def test_backfill_idempotent_active_gets_legacy(mock_db: object) -> None:
    from backend.features.billing.backfill import run_backfill

    accounts = AccountRepository(mock_db)
    subs = SubscriptionRepository(mock_db)
    active = accounts.create(
        display_name="Active",
        contact_email="active@test.local",
        status="active",
    )
    pending = accounts.create(
        display_name="Pending",
        contact_email="pending@test.local",
        status="pending",
    )
    run_backfill(mock_db)
    assert subs.get_by_account(active.id) is not None
    assert subs.get_by_account(active.id).plan_id == "legacy"
    assert subs.get_by_account(pending.id) is None
    run_backfill(mock_db)
    assert subs.get_by_account(active.id).plan_id == "legacy"


def test_legacy_plan_unlimited(mock_db: object) -> None:
    svc = _service(mock_db, enforcement=True)
    accounts = AccountRepository(mock_db)
    subs = SubscriptionRepository(mock_db)
    account = accounts.create(
        display_name="Legacy",
        contact_email="legacy@test.local",
        status="active",
    )
    subs.create_legacy(account.id)
    for _ in range(3):
        PropertyRepository(mock_db).upsert(
            Property(
                property_id=_property_id(account.id, f"P{_}"),
                name=f"P{_}",
                account_id=account.id,
            ),
            account_id=account.id,
        )
    assert svc.can_create_property(account.id)
    assert "cleaning_schedule" in svc.effective_features(account.id)
    assert not svc.mail_quota(account.id).exhausted


def test_quota_window_rolls_monthly(mock_db: object) -> None:
    subs = SubscriptionRepository(mock_db)
    accounts = AccountRepository(mock_db)
    account = accounts.create(
        display_name="Roll",
        contact_email="roll@test.local",
        status="active",
    )
    now = datetime.now(UTC)
    past = now - timedelta(days=40)
    subs._col.insert_one(
        {
            "_id": account.id,
            "account_id": account.id,
            "plan_id": "pro",
            "status": "active",
            "current_period_start": past.isoformat(),
            "current_period_end": (now + timedelta(days=330)).isoformat(),
            "quota_window_start": past.isoformat(),
            "created_at": past.isoformat(),
            "updated_at": past.isoformat(),
        }
    )
    rolled = subs.roll_quota_window(account.id, now)
    assert rolled is not None
    assert rolled.quota_window_start > past


def test_initial_sync_mails_excluded_from_quota(mock_db: object) -> None:
    svc = _service(mock_db, enforcement=True)
    accounts = AccountRepository(mock_db)
    metrics = MailMetricsRepository(mock_db)
    subs = SubscriptionRepository(mock_db)
    account = accounts.create(
        display_name="Sync",
        contact_email="sync@test.local",
        status="active",
    )
    subs.create_trial(account.id)
    sync_at = datetime.now(UTC)
    accounts._col.update_one(
        {"_id": account.id},
        {"$set": {"mail_initial_sync_completed_at": sync_at.isoformat()}},
    )
    window = subs.get_by_account(account.id).quota_window_start
    metrics.record(
        "old-mail",
        cost_usd=0.01,
        prompt_tokens=1,
        completion_tokens=1,
        account_id=account.id,
    )
    metrics._col.update_one(
        {"_id": "old-mail"},
        {"$set": {"processed_at": (sync_at - timedelta(hours=1)).isoformat()}},
    )
    metrics.record(
        "new-mail",
        cost_usd=0.01,
        prompt_tokens=1,
        completion_tokens=1,
        account_id=account.id,
    )
    quota = svc.mail_quota(account.id)
    assert quota.used == 1
    assert quota.used >= metrics.count_between(
        window, datetime.now(UTC), account_id=account.id
    )


def test_no_double_count_per_correlation_id(mock_db: object) -> None:
    metrics = MailMetricsRepository(mock_db)
    account_id = "acc-1"
    metrics.record(
        "corr-1",
        cost_usd=0.01,
        prompt_tokens=1,
        completion_tokens=1,
        account_id=account_id,
    )
    metrics.record(
        "corr-1",
        cost_usd=0.02,
        prompt_tokens=2,
        completion_tokens=2,
        account_id=account_id,
    )
    now = datetime.now(UTC)
    assert (
        metrics.count_between(now - timedelta(days=1), now, account_id=account_id) == 1
    )


def test_feature_merge_admin_toggle_survives_downgrade(mock_db: object) -> None:
    from backend.core.utils.field_crypto import FieldCipher

    svc = _service(mock_db, enforcement=False)
    accounts = AccountRepository(mock_db)
    subs = SubscriptionRepository(mock_db)
    platform = PlatformSettingsRepository(mock_db, FieldCipher(""))
    account = accounts.create(
        display_name="Feat",
        contact_email="feat@test.local",
        status="active",
    )
    subs.create_trial(account.id)
    record = platform.get(account.id) or PlatformSettingsRecord(id=account.id)
    record.features["cleaning_schedule"] = True
    platform.save(record)
    subs.set_plan(account.id, "standard", datetime.now(UTC) + timedelta(days=30))
    assert "cleaning_schedule" in svc.effective_features(account.id)
