"""Stripe-Redirect-URLs aus Settings."""

from __future__ import annotations

from backend.core.config.settings import Settings


def stripe_checkout_success_url(settings: Settings) -> str:
    if settings.stripe_checkout_success_url.strip():
        return settings.stripe_checkout_success_url.strip()
    return f"{settings.frontend_url}/settings#abo-verbrauch?checkout=success"


def stripe_checkout_cancel_url(settings: Settings) -> str:
    if settings.stripe_checkout_cancel_url.strip():
        return settings.stripe_checkout_cancel_url.strip()
    return f"{settings.frontend_url}/settings#abo-verbrauch?checkout=cancel"


def stripe_portal_return_url(settings: Settings) -> str:
    if settings.stripe_portal_return_url.strip():
        return settings.stripe_portal_return_url.strip()
    return f"{settings.frontend_url}/settings#abo-verbrauch"
