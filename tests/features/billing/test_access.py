"""Tests für Abo-Lifecycle-Zugriffslogik (access.py)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.features.billing.access import account_api_access_error, trial_expired
from backend.infrastructure.repositories.account_repository import AccountRepository
from backend.infrastructure.repositories.subscription_repository import (
    SubscriptionRepository,
)


def _account_and_subs(mock_db: object) -> tuple[object, SubscriptionRepository]:
    accounts = AccountRepository(mock_db)
    account = accounts.create(
        display_name="Tenant",
        contact_email="tenant@test.local",
        status="active",
    )
    return account, SubscriptionRepository(mock_db)


def _expire_trial(subs: SubscriptionRepository, account_id: str) -> None:
    past = datetime.now(UTC) - timedelta(days=1)
    subs._col.update_one(
        {"account_id": account_id},
        {"$set": {"current_period_end": past.isoformat()}},
    )


def test_active_trial_grants_access(mock_db: object) -> None:
    account, subs = _account_and_subs(mock_db)
    subs.create_trial(account.id)
    sub = subs.get_by_account(account.id)
    assert not trial_expired(sub)
    assert account_api_access_error(account, sub) is None


def test_expired_trial_blocks_access(mock_db: object) -> None:
    account, subs = _account_and_subs(mock_db)
    subs.create_trial(account.id)
    _expire_trial(subs, account.id)
    sub = subs.get_by_account(account.id)
    assert trial_expired(sub)
    error = account_api_access_error(account, sub)
    assert error is not None
    assert "Testphase" in error


def test_extend_trial_restores_access(mock_db: object) -> None:
    account, subs = _account_and_subs(mock_db)
    subs.create_trial(account.id)
    _expire_trial(subs, account.id)
    subs.extend_trial(account.id, days=7)
    sub = subs.get_by_account(account.id)
    assert account_api_access_error(account, sub) is None


def test_active_subscription_grants_access(mock_db: object) -> None:
    account, subs = _account_and_subs(mock_db)
    subs.create_trial(account.id)
    subs.set_plan(account.id, "standard", datetime.now(UTC) + timedelta(days=30))
    sub = subs.get_by_account(account.id)
    assert account_api_access_error(account, sub) is None


def test_past_due_blocks_access(mock_db: object) -> None:
    account, subs = _account_and_subs(mock_db)
    subs.create_trial(account.id)
    subs.set_status(account.id, "past_due")
    sub = subs.get_by_account(account.id)
    assert account_api_access_error(account, sub) is not None


def test_canceled_blocks_access(mock_db: object) -> None:
    account, subs = _account_and_subs(mock_db)
    subs.create_trial(account.id)
    subs.set_status(account.id, "canceled")
    sub = subs.get_by_account(account.id)
    assert account_api_access_error(account, sub) is not None
