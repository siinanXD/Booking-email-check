"""Sentry-Init und PII-Scrubbing (nur erfundene Daten)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from backend.api.sentry_setup import _init_sentry, _scrub_sentry_event

PHONE = "+49 151 00000000"
EMAIL = "max@example.com"
NAME = "Max Mustermann"


def _event() -> dict[str, Any]:
    frame = {"function": "send", "vars": {"guest": NAME, "phone": PHONE}}
    return {
        "message": f"Fehler für {EMAIL}, Tel {PHONE}",
        "exception": {
            "values": [
                {
                    "value": f"Kontakt {EMAIL} unter {PHONE}",
                    "stacktrace": {"frames": [frame]},
                }
            ]
        },
        "threads": {"values": [{"stacktrace": {"frames": [dict(frame)]}}]},
        "breadcrumbs": {"values": [{"message": f"Sende an {PHONE} / {EMAIL}"}]},
        "logentry": {
            "message": f"Gast %s {PHONE}",
            "formatted": f"Gast {EMAIL}",
            "params": [NAME, PHONE],
        },
        "extra": {"guest_name": NAME, "phone": PHONE},
    }


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


def test_scrub_sentry_event_removes_all_guest_data() -> None:
    """Telefon, E-Mail und Name stehen nach dem Scrubbing nirgends mehr."""
    out = _scrub_sentry_event(_event(), {})
    dumped = repr(out)
    assert PHONE not in dumped
    assert EMAIL not in dumped
    assert NAME not in dumped
    assert "extra" not in out
    assert "params" not in out["logentry"]
    exc = out["exception"]["values"][0]
    assert "vars" not in exc["stacktrace"]["frames"][0]
    assert "vars" not in out["threads"]["values"][0]["stacktrace"]["frames"][0]
    assert "[PHONE]" in out["breadcrumbs"]["values"][0]["message"]
    assert "[EMAIL]" in out["logentry"]["formatted"]


def test_scrub_sentry_event_tolerates_missing_sections() -> None:
    """Fehlende oder leere Abschnitte lassen das Scrubbing nicht scheitern."""
    assert _scrub_sentry_event({}, {}) == {}
    assert _scrub_sentry_event({"logentry": None, "exception": None}, {})


def test_init_sentry_noop_without_dsn() -> None:
    """Ohne DSN initialisiert Sentry nicht und wirft nicht."""
    with patch("sentry_sdk.init") as init:
        _init_sentry(SimpleNamespace(sentry_dsn=None))  # type: ignore[arg-type]
    init.assert_not_called()


def test_init_sentry_disables_local_variables_and_pii() -> None:
    """Rot, sobald jemand include_local_variables oder send_default_pii einschaltet."""
    cfg = SimpleNamespace(
        sentry_dsn="https://key@example.invalid/1",
        app_env="test",
        sentry_traces_sample_rate=0.0,
    )
    with patch("sentry_sdk.init") as init:
        _init_sentry(cfg)  # type: ignore[arg-type]
    kwargs = init.call_args.kwargs
    assert kwargs["include_local_variables"] is False
    assert kwargs["send_default_pii"] is False
    assert kwargs["max_request_body_size"] == "never"
    assert kwargs["before_send"] is _scrub_sentry_event
