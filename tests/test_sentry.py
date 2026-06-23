"""Sentry-Init und PII-Scrubbing."""

from __future__ import annotations

from types import SimpleNamespace

from backend.api.app import _init_sentry, _scrub_sentry_event


def test_scrub_sentry_event_masks_pii() -> None:
    """E-Mail/Telefon in Message und Exception-Werten werden maskiert."""
    event = {
        "message": "Fehler für gast@example.com, Tel +49 170 1234567",
        "exception": {"values": [{"value": "Kontakt admin@host.de"}]},
    }
    out = _scrub_sentry_event(event, {})
    assert "gast@example.com" not in out["message"]
    assert "[EMAIL]" in out["message"] and "[PHONE]" in out["message"]
    assert "admin@host.de" not in out["exception"]["values"][0]["value"]
    assert "[EMAIL]" in out["exception"]["values"][0]["value"]


def test_init_sentry_noop_without_dsn() -> None:
    """Ohne DSN initialisiert Sentry nicht und wirft nicht."""
    _init_sentry(SimpleNamespace(sentry_dsn=None))  # type: ignore[arg-type]
