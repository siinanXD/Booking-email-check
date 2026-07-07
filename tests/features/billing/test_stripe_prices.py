"""Tests für Plan ↔ Stripe-Price Mapping."""

from __future__ import annotations

from backend.core.config.settings import Settings
from backend.features.billing.plans import plan_id_for_price, price_id_for_plan


def _stripe_settings() -> Settings:
    return Settings.model_validate(
        {
            "OPENAI_API_KEY": "sk-test",
            "MONGODB_URI": "mongodb://localhost",
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test",
            "STRIPE_PRICE_STANDARD": "price_std",
            "STRIPE_PRICE_PRO": "price_pro",
            "STRIPE_PRICE_BUSINESS": "price_biz",
        }
    )


def test_price_id_for_plan() -> None:
    settings = _stripe_settings()
    assert price_id_for_plan(settings, "standard") == "price_std"
    assert price_id_for_plan(settings, "trial") is None


def test_plan_id_for_price_reverse_lookup() -> None:
    settings = _stripe_settings()
    assert plan_id_for_price(settings, "price_pro") == "pro"
    assert plan_id_for_price(settings, "unknown") is None
