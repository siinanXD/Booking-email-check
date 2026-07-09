"""Tests: Webhook-Routing in den WhatsApp-Bot (WHATSAPP_BOT_ENABLED)."""

from __future__ import annotations

from typing import Any

from backend.core.config.settings import Settings
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRecord,
)


def _bot_payload(text: str = "Hallo", sender: str = "4915711111111") -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "111222333"},
                            "contacts": [{"profile": {"name": "Anna"}}],
                            "messages": [
                                {
                                    "id": "wamid.bot1",
                                    "from": sender,
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        }
                    }
                ]
            }
        ],
    }


def _register_phone_number(app: Any, account_id: str) -> None:
    ctx = app.extensions["ctx"]
    ctx.platform_settings_repo.save(
        PlatformSettingsRecord(
            id=account_id,
            whatsapp_phone_number_id="111222333",
        )
    )


def test_bot_mode_unbekannte_nummer(
    client: Any,
    app: Any,
    web_settings: Settings,
    tenant_account_id: str,
) -> None:
    """Bot aktiv: unbekannte Absender werden höflich abgelehnt (kein Forward)."""
    _register_phone_number(app, tenant_account_id)
    web_settings.whatsapp_bot_enabled = True
    try:
        resp = client.post("/api/whatsapp/webhook", json=_bot_payload())
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "unknown_sender"
    finally:
        web_settings.whatsapp_bot_enabled = False


def test_bot_mode_aus_nutzt_forwarding(
    client: Any,
    app: Any,
    tenant_account_id: str,
) -> None:
    """Bot inaktiv: bestehender Weiterleitungs-Pfad bleibt unverändert."""
    _register_phone_number(app, tenant_account_id)
    resp = client.post("/api/whatsapp/webhook", json=_bot_payload())
    assert resp.status_code == 200
    # kein Host mit WhatsApp-Nummer hinterlegt → skipped (Forward-Pfad)
    assert resp.get_json()["status"] == "skipped"


def test_bot_mode_bekannter_owner_wird_verarbeitet(
    client: Any,
    app: Any,
    web_settings: Settings,
    tenant_account_id: str,
) -> None:
    """Bot aktiv: bekannte Nummer wird als Sender aufgelöst und verarbeitet."""
    _register_phone_number(app, tenant_account_id)
    ctx = app.extensions["ctx"]
    user = ctx.user_repo.create(
        "bot-owner@test.local",
        "hash",
        account_id=tenant_account_id,
        role="owner",
        first_name="Olaf",
    )
    ctx.user_repo.update_whatsapp_profile(
        user.id,
        whatsapp_phone_e164="+4915711111111",
        whatsapp_enabled=True,
    )
    web_settings.whatsapp_bot_enabled = True
    try:
        resp = client.post("/api/whatsapp/webhook", json=_bot_payload("Hilfe"))
        assert resp.status_code == 200
        # MockLLM liefert kein Intent-JSON → Bot antwortet mit Rückfrage,
        # der Versand scheitert mangels Credentials — Status bleibt handled.
        assert resp.get_json()["status"] == "handled"
    finally:
        web_settings.whatsapp_bot_enabled = False
