"""Persistenz von Mandanten-Abos."""

from __future__ import annotations

import calendar
from datetime import UTC, datetime, timedelta
from typing import Any

from pymongo.collection import Collection
from pymongo.errors import OperationFailure

from backend.features.billing.plans import TRIAL_DAYS
from backend.infrastructure.repositories._subscription_models import (
    SubscriptionRecord,
    SubscriptionStatus,
)
from backend.infrastructure.repositories._subscription_stripe import (
    apply_stripe_subscription as _apply_stripe_subscription,
)
from backend.infrastructure.repositories._subscription_stripe import (
    get_by_stripe_customer as _get_by_stripe_customer,
)
from backend.infrastructure.repositories._subscription_stripe import (
    set_stripe_ids as _set_stripe_ids,
)
from backend.infrastructure.repositories.mongo import Db

_TRIAL_DELTA = timedelta(days=TRIAL_DAYS)


def _add_months(dt: datetime, months: int) -> datetime:
    """Schiebt ein Datum um N Monate (Kalendermonate)."""
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(dt.day, last_day)
    return dt.replace(year=year, month=month, day=day, tzinfo=dt.tzinfo)


def _record_from_doc(doc: dict[str, Any]) -> SubscriptionRecord:
    payload = {k: v for k, v in doc.items() if k != "_id"}
    payload["account_id"] = doc.get("account_id") or doc["_id"]
    return SubscriptionRecord.model_validate(payload)


class SubscriptionRepository:
    """Collection `subscriptions` — ein Dokument pro Account."""

    COLLECTION = "subscriptions"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]
        self._col.create_index("account_id", unique=True, name="idx_sub_account")
        self._ensure_stripe_customer_index()

    def _ensure_stripe_customer_index(self) -> None:
        # Partial-Index: nur nicht-leere stripe_customer_id sind eindeutig.
        # sparse reicht nicht, da das Feld als "" (nicht fehlend) gespeichert wird.
        name = "idx_sub_stripe_customer"
        options: dict[str, Any] = {
            "unique": True,
            "name": name,
            "partialFilterExpression": {"stripe_customer_id": {"$gt": ""}},
        }
        try:
            self._col.create_index("stripe_customer_id", **options)
        except OperationFailure:
            # Alte (sparse) Index-Definition kollidiert → neu aufbauen.
            self._col.drop_index(name)
            self._col.create_index("stripe_customer_id", **options)

    def get_by_account(self, account_id: str) -> SubscriptionRecord | None:
        """Lädt Abo per account_id."""
        doc = self._col.find_one({"account_id": account_id})
        if doc is None:
            doc = self._col.find_one({"_id": account_id})
        if doc is None:
            return None
        return _record_from_doc(doc)

    def _insert(self, record: SubscriptionRecord) -> SubscriptionRecord:
        now = datetime.now(UTC)
        doc = record.model_dump(mode="json")
        doc["_id"] = record.account_id
        doc["account_id"] = record.account_id
        doc["created_at"] = now.isoformat()
        doc["updated_at"] = now.isoformat()
        self._col.insert_one(doc)
        return _record_from_doc(doc)

    def create_trial(self, account_id: str) -> SubscriptionRecord:
        """Legt Trial-Abo an (14 Tage ab jetzt)."""
        now = datetime.now(UTC)
        record = SubscriptionRecord(
            account_id=account_id,
            plan_id="trial",
            status="trialing",
            current_period_start=now,
            current_period_end=now + _TRIAL_DELTA,
            quota_window_start=now,
            created_at=now,
            updated_at=now,
        )
        return self._insert(record)

    def create_legacy(self, account_id: str) -> SubscriptionRecord:
        """Legt Legacy-Abo für Bestandskunden an."""
        now = datetime.now(UTC)
        far_future = now + timedelta(days=365 * 100)
        record = SubscriptionRecord(
            account_id=account_id,
            plan_id="legacy",
            status="active",
            current_period_start=now,
            current_period_end=far_future,
            quota_window_start=now,
            created_at=now,
            updated_at=now,
        )
        return self._insert(record)

    def get_by_stripe_customer(self, customer_id: str) -> SubscriptionRecord | None:
        """Lädt Abo per Stripe-Customer-ID."""
        return _get_by_stripe_customer(self._col, customer_id, _record_from_doc)

    def set_stripe_ids(
        self,
        account_id: str,
        *,
        customer_id: str | None = None,
        subscription_id: str | None = None,
    ) -> SubscriptionRecord | None:
        """Speichert Stripe-Customer- und/oder Subscription-ID."""
        return _set_stripe_ids(
            self._col,
            account_id,
            customer_id=customer_id,
            subscription_id=subscription_id,
            get_by_account=self.get_by_account,
        )

    def apply_stripe_subscription(
        self,
        account_id: str,
        *,
        plan_id: str,
        status: SubscriptionStatus,
        period_start: datetime,
        period_end: datetime,
        customer_id: str | None = None,
        subscription_id: str | None = None,
    ) -> SubscriptionRecord | None:
        """Synchronisiert Abo aus Stripe-Webhook."""
        return _apply_stripe_subscription(
            self._col,
            account_id,
            plan_id=plan_id,
            status=status,
            period_start=period_start,
            period_end=period_end,
            customer_id=customer_id,
            subscription_id=subscription_id,
            get_by_account=self.get_by_account,
            create_trial=self.create_trial,
        )

    def set_plan_with_status(
        self,
        account_id: str,
        plan_id: str,
        status: SubscriptionStatus,
        period_end: datetime,
        *,
        period_start: datetime | None = None,
    ) -> SubscriptionRecord | None:
        """Setzt Plan und Status (Webhook: past_due/canceled)."""
        sub = self.get_by_account(account_id)
        if sub is None:
            return None
        now = datetime.now(UTC)
        start = period_start or sub.current_period_start
        self._col.update_one(
            {"account_id": account_id},
            {
                "$set": {
                    "plan_id": plan_id,
                    "status": status,
                    "current_period_start": start.isoformat(),
                    "current_period_end": period_end.isoformat(),
                    "updated_at": now.isoformat(),
                }
            },
        )
        return self.get_by_account(account_id)

    def set_plan(
        self,
        account_id: str,
        plan_id: str,
        period_end: datetime,
    ) -> SubscriptionRecord | None:
        """Setzt Plan und aktiviert Abo."""
        now = datetime.now(UTC)
        update = {
            "plan_id": plan_id,
            "status": "active",
            "current_period_start": now.isoformat(),
            "current_period_end": period_end.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = self._col.update_one(
            {"account_id": account_id},
            {"$set": update},
        )
        if result.matched_count == 0:
            return None
        return self.get_by_account(account_id)

    def extend_trial(self, account_id: str, days: int) -> SubscriptionRecord | None:
        """Verlängert Trial um N Tage."""
        sub = self.get_by_account(account_id)
        if sub is None:
            return None
        now = datetime.now(UTC)
        base = sub.current_period_end if sub.current_period_end > now else now
        new_end = base + timedelta(days=days)
        self._col.update_one(
            {"account_id": account_id},
            {
                "$set": {
                    "status": "trialing",
                    "plan_id": "trial",
                    "current_period_end": new_end.isoformat(),
                    "updated_at": now.isoformat(),
                }
            },
        )
        return self.get_by_account(account_id)

    def set_overrides(
        self,
        account_id: str,
        *,
        override_max_mails: int | None = None,
        override_max_properties: int | None = None,
        override_max_users: int | None = None,
        clear_unset: bool = False,
    ) -> SubscriptionRecord | None:
        """Setzt Admin-Limit-Overrides."""
        if self.get_by_account(account_id) is None:
            return None
        now = datetime.now(UTC)
        fields = {
            "override_max_mails": override_max_mails,
            "override_max_properties": override_max_properties,
            "override_max_users": override_max_users,
        }
        if clear_unset:
            update: dict[str, Any] = {k: v for k, v in fields.items()}
        else:
            update = {k: v for k, v in fields.items() if v is not None}
        update["updated_at"] = now.isoformat()
        self._col.update_one({"account_id": account_id}, {"$set": update})
        return self.get_by_account(account_id)

    def roll_quota_window(
        self, account_id: str, now: datetime
    ) -> SubscriptionRecord | None:
        """Schiebt quota_window_start monatlich vor (lazy rollover)."""
        sub = self.get_by_account(account_id)
        if sub is None:
            return None
        window_start = sub.quota_window_start
        advanced = window_start
        while now >= _add_months(advanced, 1):
            advanced = _add_months(advanced, 1)
        if advanced == window_start:
            return sub
        self._col.update_one(
            {"account_id": account_id},
            {
                "$set": {
                    "quota_window_start": advanced.isoformat(),
                    "updated_at": now.isoformat(),
                }
            },
        )
        return self.get_by_account(account_id)

    def list_all_account_ids(self) -> list[str]:
        """Alle account_ids mit Abo."""
        return [str(doc["account_id"]) for doc in self._col.find({}, {"account_id": 1})]

    def set_status(
        self,
        account_id: str,
        status: SubscriptionStatus,
    ) -> SubscriptionRecord | None:
        """Aktualisiert Abo-Status."""
        now = datetime.now(UTC)
        result = self._col.update_one(
            {"account_id": account_id},
            {"$set": {"status": status, "updated_at": now.isoformat()}},
        )
        if result.matched_count == 0:
            return None
        return self.get_by_account(account_id)
