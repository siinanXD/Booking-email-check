"""Backfill: legt fehlende Subscriptions für Bestandskunden an."""

from __future__ import annotations

from typing import Any


def run_backfill(db: Any) -> tuple[int, int]:
    """Legt legacy-Abos für aktive Accounts ohne Subscription an."""
    from backend.infrastructure.repositories.account_repository import AccountRepository
    from backend.infrastructure.repositories.subscription_repository import (
        SubscriptionRepository,
    )

    accounts = AccountRepository(db)
    subscriptions = SubscriptionRepository(db)
    existing = set(subscriptions.list_all_account_ids())
    created_legacy = 0
    skipped = 0

    for account in accounts.list_by_status(None):
        if account.id in existing:
            skipped += 1
            continue
        if account.status != "active":
            skipped += 1
            continue
        subscriptions.create_legacy(account.id)
        existing.add(account.id)
        created_legacy += 1

    return created_legacy, skipped
