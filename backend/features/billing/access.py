"""Account-Zugriff unter Berücksichtigung von Abo-Lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.infrastructure.repositories._subscription_models import SubscriptionRecord
from backend.infrastructure.repositories.account_repository import AccountRecord

_ACTIVE_SUB_STATUSES = frozenset({"trialing", "active"})


def account_api_access_error(
    account: AccountRecord | None,
    subscription: SubscriptionRecord | None,
) -> str | None:
    """Liefert Fehlermeldung wenn API-Zugriff blockiert ist.

    Vorrang: suspended → Abo-Status → expires_at-Fallback.
    """
    if account is None:
        return None
    if account.status == "suspended":
        return "Dein Konto wurde vorübergehend gesperrt."
    if subscription is not None:
        if subscription.status in _ACTIVE_SUB_STATUSES:
            return None
        if subscription.status == "past_due":
            return "Zahlung ausstehend — Zugang vorübergehend gesperrt."
        if subscription.status == "canceled":
            return "Abo beendet — Zugang gesperrt."
    if account.expires_at is not None and account.expires_at < datetime.now(UTC):
        return "Zugang abgelaufen"
    return None
