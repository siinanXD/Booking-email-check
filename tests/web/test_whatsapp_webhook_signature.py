"""Tests: WhatsApp-Webhook-Signaturprüfung (fail-closed in Produktion)."""

from __future__ import annotations

import hashlib
import hmac

from flask import Flask, g, request

from backend.api.blueprints.whatsapp_webhook import _verify_signature
from backend.core.config.settings import Settings


def _settings(**overrides: str) -> Settings:
    payload = {
        "OPENAI_API_KEY": "sk-test",
        "MONGODB_URI": "mongodb://localhost",
        "LANGFUSE_PUBLIC_KEY": "pk-test",
        "LANGFUSE_SECRET_KEY": "sk-test",
        "FLASK_SECRET_KEY": "x" * 32,
        "LLM_MODE": "mock",
        **overrides,
    }
    return Settings.model_validate(payload)


def _check(settings: Settings, body: bytes, headers: dict[str, str]) -> bool:
    app = Flask(__name__)
    with app.test_request_context(
        "/api/whatsapp/webhook", method="POST", data=body, headers=headers
    ):
        g.settings = settings
        return _verify_signature(request)


def test_missing_secret_rejected_in_production() -> None:
    settings = _settings(APP_ENV="production", FLASK_ENV="production")
    assert _check(settings, b"{}", {}) is False


def test_missing_secret_allowed_in_development() -> None:
    settings = _settings(APP_ENV="development", FLASK_ENV="development")
    assert _check(settings, b"{}", {}) is True


def test_valid_signature_accepted() -> None:
    secret = "meta-app-secret"
    body = b'{"object": "whatsapp_business_account"}'
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    settings = _settings(
        APP_ENV="production",
        FLASK_ENV="production",
        WHATSAPP_APP_SECRET=secret,
    )
    headers = {"X-Hub-Signature-256": f"sha256={digest}"}
    assert _check(settings, body, headers) is True


def test_invalid_signature_rejected() -> None:
    settings = _settings(
        APP_ENV="production",
        FLASK_ENV="production",
        WHATSAPP_APP_SECRET="meta-app-secret",
    )
    headers = {"X-Hub-Signature-256": "sha256=deadbeef"}
    assert _check(settings, b"{}", headers) is False
