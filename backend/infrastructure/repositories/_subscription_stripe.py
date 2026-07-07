"""Stripe-spezifische Subscription-Repository-Operationen."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pymongo.collection import Collection
from pymongo.errors import OperationFailure

from backend.infrastructure.repositories._subscription_models import (
    SubscriptionRecord,
    SubscriptionStatus,
)


def ensure_stripe_customer_index(col: Collection[dict[str, Any]]) -> None:
    """Partial-Unique-Index: nur nicht-leere stripe_customer_id sind eindeutig.

    sparse reicht nicht, da das Feld als "" (nicht fehlend) gespeichert wird —
    mehrere Trial/Legacy-Abos mit "" verletzen sonst die Unique-Bedingung.
    """
    name = "idx_sub_stripe_customer"
    options: dict[str, Any] = {
        "unique": True,
        "name": name,
        "partialFilterExpression": {"stripe_customer_id": {"$gt": ""}},
    }
    try:
        col.create_index("stripe_customer_id", **options)
    except OperationFailure:
        col.drop_index(name)
        col.create_index("stripe_customer_id", **options)


def get_by_stripe_customer(
    col: Collection[dict[str, Any]],
    customer_id: str,
    record_from_doc: Callable[[dict[str, Any]], SubscriptionRecord],
) -> SubscriptionRecord | None:
    if not customer_id.strip():
        return None
    doc = col.find_one({"stripe_customer_id": customer_id})
    if doc is None:
        return None
    return record_from_doc(doc)


def set_stripe_ids(
    col: Collection[dict[str, Any]],
    account_id: str,
    *,
    customer_id: str | None = None,
    subscription_id: str | None = None,
    get_by_account: Callable[[str], SubscriptionRecord | None],
) -> SubscriptionRecord | None:
    if get_by_account(account_id) is None:
        return None
    now = datetime.now(UTC)
    update: dict[str, Any] = {"updated_at": now.isoformat()}
    if customer_id is not None:
        update["stripe_customer_id"] = customer_id
    if subscription_id is not None:
        update["stripe_subscription_id"] = subscription_id
    col.update_one({"account_id": account_id}, {"$set": update})
    return get_by_account(account_id)


def apply_stripe_subscription(
    col: Collection[dict[str, Any]],
    account_id: str,
    *,
    plan_id: str,
    status: SubscriptionStatus,
    period_start: datetime,
    period_end: datetime,
    customer_id: str | None = None,
    subscription_id: str | None = None,
    get_by_account: Callable[[str], SubscriptionRecord | None],
    create_trial: Callable[[str], SubscriptionRecord],
) -> SubscriptionRecord | None:
    if get_by_account(account_id) is None:
        create_trial(account_id)
    now = datetime.now(UTC)
    update: dict[str, Any] = {
        "plan_id": plan_id,
        "status": status,
        "current_period_start": period_start.isoformat(),
        "current_period_end": period_end.isoformat(),
        "updated_at": now.isoformat(),
    }
    if customer_id is not None:
        update["stripe_customer_id"] = customer_id
    if subscription_id is not None:
        update["stripe_subscription_id"] = subscription_id
    col.update_one({"account_id": account_id}, {"$set": update})
    return get_by_account(account_id)
