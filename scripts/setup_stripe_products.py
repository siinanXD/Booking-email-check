"""Legt Stripe-Produkte und monatliche Preise an (idempotent)."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    """Erzeugt Standard/Pro/Business in Stripe und gibt Price-IDs aus."""
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    import stripe

    from backend.core.config.settings import get_settings
    from backend.features.billing.plans import CHECKOUT_PLAN_IDS, PLANS

    settings = get_settings()
    if not settings.stripe_secret_key.strip():
        print("STRIPE_SECRET_KEY nicht gesetzt.")
        return 1
    stripe.api_key = settings.stripe_secret_key

    price_env_keys = {
        "standard": "STRIPE_PRICE_STANDARD",
        "pro": "STRIPE_PRICE_PRO",
        "business": "STRIPE_PRICE_BUSINESS",
    }

    print("# Trage diese Werte in .env ein:\n")
    for plan_id in CHECKOUT_PLAN_IDS:
        plan = PLANS[plan_id]
        lookup_key = f"booking_email_{plan_id}_monthly"
        existing = stripe.Price.list(lookup_keys=[lookup_key], active=True, limit=1)
        if existing.data:
            price_id = existing.data[0]["id"]
        else:
            products = stripe.Product.list(active=True, limit=100)
            product = next(
                (
                    p
                    for p in products.data
                    if p.get("metadata", {}).get("plan_id") == plan_id
                ),
                None,
            )
            if product is None:
                product = stripe.Product.create(
                    name=f"Mail Assistant AI — {plan.display_name}",
                    metadata={"plan_id": plan_id},
                )
            price = stripe.Price.create(
                product=product["id"],
                unit_amount=plan.price_eur_monthly * 100,
                currency="eur",
                recurring={"interval": "month"},
                lookup_key=lookup_key,
                transfer_lookup_key=True,
                metadata={"plan_id": plan_id},
            )
            price_id = price["id"]
        env_key = price_env_keys[plan_id]
        print(
            f"{env_key}={price_id}  # {plan.display_name} ({plan.price_eur_monthly} EUR/Monat)"
        )

    print("\nWebhook-Endpoint: POST /api/billing/webhook")
    print("Customer Portal im Stripe-Dashboard aktivieren (Plan-Wechsel erlauben).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
