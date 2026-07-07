"""Stripe Checkout + Customer Portal für Mandanten-Abos."""

from __future__ import annotations

import logging
from typing import Any

import stripe

from backend.core.config.settings import Settings
from backend.features.billing.plans import CHECKOUT_PLAN_IDS, price_id_for_plan
from backend.features.billing.stripe_urls import (
    stripe_checkout_cancel_url,
    stripe_checkout_success_url,
    stripe_portal_return_url,
)
from backend.infrastructure.repositories.account_repository import AccountRepository
from backend.infrastructure.repositories.subscription_repository import (
    SubscriptionRepository,
)
from backend.infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class StripeBillingError(Exception):
    """Fachlicher Fehler bei Stripe-Operationen."""


class StripeService:
    """Erzeugt Checkout- und Portal-Sessions."""

    def __init__(
        self,
        settings: Settings,
        subscription_repo: SubscriptionRepository,
        account_repo: AccountRepository,
        user_repo: UserRepository,
    ) -> None:
        self._settings = settings
        self._subscription_repo = subscription_repo
        self._account_repo = account_repo
        self._user_repo = user_repo
        stripe.api_key = settings.stripe_secret_key

    @property
    def enabled(self) -> bool:
        return bool(
            self._settings.stripe_enabled and self._settings.stripe_secret_key.strip()
        )

    def ensure_customer(self, account_id: str) -> str:
        """Gibt Stripe-Customer-ID zurück; legt Customer bei Bedarf an."""
        sub = self._subscription_repo.get_by_account(account_id)
        if sub is not None and sub.stripe_customer_id.strip():
            return sub.stripe_customer_id
        account = self._account_repo.get_by_id(account_id)
        if account is None:
            raise StripeBillingError("Account nicht gefunden")
        email = account.contact_email
        users = self._user_repo.list_by_account_id(account_id)
        if users:
            email = users[0].email
        customer = stripe.Customer.create(
            email=email,
            name=account.display_name,
            metadata={"account_id": account_id},
        )
        customer_id = str(customer["id"])
        if sub is None:
            self._subscription_repo.create_trial(account_id)
        self._subscription_repo.set_stripe_ids(account_id, customer_id=customer_id)
        return customer_id

    def create_checkout_session(self, account_id: str, plan_id: str) -> str:
        """Startet Stripe Checkout für einen bezahlten Plan."""
        if plan_id not in CHECKOUT_PLAN_IDS:
            raise StripeBillingError("Plan nicht per Checkout verfügbar")
        price_id = price_id_for_plan(self._settings, plan_id)
        if not price_id:
            raise StripeBillingError("Stripe-Preis für Plan nicht konfiguriert")
        customer_id = self.ensure_customer(account_id)
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            client_reference_id=account_id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=stripe_checkout_success_url(self._settings),
            cancel_url=stripe_checkout_cancel_url(self._settings),
            metadata={"account_id": account_id, "plan_id": plan_id},
        )
        url = session.get("url")
        if not url:
            raise StripeBillingError("Checkout-URL fehlt")
        return str(url)

    def create_portal_session(self, account_id: str) -> str:
        """Öffnet Stripe Customer Portal (Upgrade/Downgrade/Kündigung)."""
        sub = self._subscription_repo.get_by_account(account_id)
        customer_id = sub.stripe_customer_id if sub else ""
        if not customer_id.strip():
            customer_id = self.ensure_customer(account_id)
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=stripe_portal_return_url(self._settings),
        )
        url = session.get("url")
        if not url:
            raise StripeBillingError("Portal-URL fehlt")
        return str(url)

    def construct_event(self, payload: bytes, sig_header: str) -> Any:
        """Verifiziert Webhook-Signatur und liefert Stripe-Event."""
        secret = self._settings.stripe_webhook_secret.strip()
        if not secret:
            raise StripeBillingError("Webhook-Secret nicht konfiguriert")
        return stripe.Webhook.construct_event(payload, sig_header, secret)
