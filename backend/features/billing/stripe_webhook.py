"""Stripe-Webhook → SubscriptionRepository."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from backend.core.config.settings import Settings
from backend.features.billing.plans import plan_id_for_price
from backend.features.billing.stripe_service import StripeBillingError, StripeService
from backend.infrastructure.repositories._subscription_models import SubscriptionStatus
from backend.infrastructure.repositories.subscription_repository import (
    SubscriptionRepository,
)

logger = logging.getLogger(__name__)

_STRIPE_STATUS_MAP: dict[str, SubscriptionStatus] = {
    "trialing": "trialing",
    "active": "active",
    "past_due": "past_due",
    "unpaid": "past_due",
    "canceled": "canceled",
    "incomplete": "past_due",
    "incomplete_expired": "canceled",
    "paused": "past_due",
}


class StripeWebhookHandler:
    """Mappt Stripe-Events auf lokale Abo-Daten."""

    def __init__(
        self,
        settings: Settings,
        subscription_repo: SubscriptionRepository,
        stripe_service: StripeService,
    ) -> None:
        self._settings = settings
        self._subscription_repo = subscription_repo
        self._stripe_service = stripe_service

    def handle(self, payload: bytes, sig_header: str) -> None:
        """Verarbeitet ein signiertes Stripe-Webhook-Event."""
        try:
            event = self._stripe_service.construct_event(payload, sig_header)
        except StripeBillingError:
            raise
        except Exception as exc:
            logger.warning("Stripe webhook signature failed: %s", exc)
            raise StripeBillingError("Ungültige Webhook-Signatur") from exc

        event_type = str(event.get("type", ""))
        data_object = event.get("data", {}).get("object", {})
        if event_type == "checkout.session.completed":
            self._on_checkout_completed(data_object)
        elif event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
        }:
            self._on_subscription_changed(data_object)
        elif event_type == "customer.subscription.deleted":
            self._on_subscription_deleted(data_object)
        elif event_type == "invoice.payment_failed":
            self._on_payment_failed(data_object)

    def _account_id_from_customer(self, customer_id: str) -> str | None:
        sub = self._subscription_repo.get_by_stripe_customer(customer_id)
        return sub.account_id if sub else None

    def _plan_from_subscription(self, stripe_sub: dict[str, Any]) -> str | None:
        items = stripe_sub.get("items", {}).get("data", [])
        if not items:
            return None
        price = items[0].get("price", {})
        price_id = str(price.get("id", ""))
        return plan_id_for_price(self._settings, price_id)

    def _period_bounds(self, stripe_sub: dict[str, Any]) -> tuple[datetime, datetime]:
        start = datetime.fromtimestamp(
            int(stripe_sub.get("current_period_start", 0)), tz=UTC
        )
        end = datetime.fromtimestamp(
            int(stripe_sub.get("current_period_end", 0)), tz=UTC
        )
        return start, end

    def _map_status(self, stripe_status: str) -> SubscriptionStatus:
        return _STRIPE_STATUS_MAP.get(stripe_status, "active")

    def _on_checkout_completed(self, session: dict[str, Any]) -> None:
        account_id = str(session.get("client_reference_id") or "")
        if not account_id:
            metadata = session.get("metadata") or {}
            account_id = str(metadata.get("account_id") or "")
        if not account_id:
            logger.warning("checkout.session.completed ohne account_id")
            return
        customer_id = str(session.get("customer") or "")
        subscription_id = str(session.get("subscription") or "")
        if customer_id:
            self._subscription_repo.set_stripe_ids(
                account_id,
                customer_id=customer_id,
                subscription_id=subscription_id or None,
            )

    def _on_subscription_changed(self, stripe_sub: dict[str, Any]) -> None:
        customer_id = str(stripe_sub.get("customer") or "")
        account_id = self._account_id_from_customer(customer_id)
        if not account_id:
            logger.warning("subscription event ohne bekannten account: %s", customer_id)
            return
        plan_id = self._plan_from_subscription(stripe_sub)
        if not plan_id:
            logger.warning(
                "subscription event ohne Plan-Mapping: %s",
                stripe_sub.get("id"),
            )
            return
        period_start, period_end = self._period_bounds(stripe_sub)
        status = self._map_status(str(stripe_sub.get("status", "active")))
        self._subscription_repo.apply_stripe_subscription(
            account_id,
            plan_id=plan_id,
            status=status,
            period_start=period_start,
            period_end=period_end,
            customer_id=customer_id,
            subscription_id=str(stripe_sub.get("id") or ""),
        )

    def _on_subscription_deleted(self, stripe_sub: dict[str, Any]) -> None:
        customer_id = str(stripe_sub.get("customer") or "")
        account_id = self._account_id_from_customer(customer_id)
        if not account_id:
            return
        period_start, period_end = self._period_bounds(stripe_sub)
        plan_id = self._plan_from_subscription(stripe_sub) or "trial"
        self._subscription_repo.set_plan_with_status(
            account_id,
            plan_id,
            "canceled",
            period_end,
            period_start=period_start,
        )

    def _on_payment_failed(self, invoice: dict[str, Any]) -> None:
        customer_id = str(invoice.get("customer") or "")
        account_id = self._account_id_from_customer(customer_id)
        if not account_id:
            return
        sub = self._subscription_repo.get_by_account(account_id)
        if sub is None:
            return
        self._subscription_repo.set_status(account_id, "past_due")
