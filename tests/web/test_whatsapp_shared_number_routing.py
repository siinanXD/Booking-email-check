"""Tests: geteilte Plattform-Nummer – Webhook routet über die Absendernummer.

Wenn ``WHATSAPP_PHONE_NUMBER_ID`` (die zentrale Betreiber-Nummer) auf die
eingehende ``phone_number_id`` passt, bestimmt der Absender den Mandanten –
so können sich mehrere Konten eine Nummer teilen, sauber getrennt.
"""

from __future__ import annotations

from typing import Any

from backend.core.config.settings import Settings
from backend.features.cleaning.models import CleaningPartner

_PLATFORM_PNID = "PLAT999"


def _payload(sender: str, *, pnid: str = _PLATFORM_PNID, text: str = "Hallo") -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": pnid},
                            "contacts": [{"profile": {"name": "Anna"}}],
                            "messages": [
                                {
                                    "id": "wamid.s1",
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


def _add_partner(
    app: Any, account_id: str, phone: str, *, partner_id: str = "p1"
) -> None:
    ctx = app.extensions["ctx"]
    ctx.cleaning_partner_repo.upsert(
        CleaningPartner(
            partner_id=partner_id,
            account_id=account_id,
            name="Putzkraft",
            phone=phone,
            active=True,
        ),
        account_id=account_id,
    )


def test_shared_number_routes_cleaner_to_account(
    client: Any, app: Any, web_settings: Settings, tenant_account_id: str
) -> None:
    """Bekannter Absender auf der geteilten Nummer → an sein Konto, verarbeitet."""
    web_settings.whatsapp_phone_number_id = _PLATFORM_PNID
    web_settings.whatsapp_bot_enabled = True
    _add_partner(app, tenant_account_id, "+491705550001")
    try:
        resp = client.post("/api/whatsapp/webhook", json=_payload("491705550001"))
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "handled"
    finally:
        web_settings.whatsapp_bot_enabled = False
        web_settings.whatsapp_phone_number_id = ""


def test_shared_number_unknown_sender(
    client: Any, app: Any, web_settings: Settings, tenant_account_id: str
) -> None:
    """Absender in keinem Konto → höfliche Ablehnung, keine Fehlzuordnung."""
    web_settings.whatsapp_phone_number_id = _PLATFORM_PNID
    web_settings.whatsapp_bot_enabled = True
    try:
        resp = client.post("/api/whatsapp/webhook", json=_payload("490000000000"))
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "unknown_sender"
    finally:
        web_settings.whatsapp_bot_enabled = False
        web_settings.whatsapp_phone_number_id = ""


def test_shared_number_ambiguous_sender(
    client: Any, app: Any, web_settings: Settings, tenant_account_id: str
) -> None:
    """Dieselbe Nummer in zwei Konten → ambiguous statt falscher Zuordnung."""
    web_settings.whatsapp_phone_number_id = _PLATFORM_PNID
    web_settings.whatsapp_bot_enabled = True
    ctx = app.extensions["ctx"]
    other = ctx.account_repo.create(
        display_name="Kunde B",
        contact_email="kunde-b@example.de",
        account_type="business",
        company_name="Kunde B",
        status="active",
    )
    _add_partner(app, tenant_account_id, "+491705550001", partner_id="p1")
    _add_partner(app, other.id, "+491705550001", partner_id="p2")
    try:
        resp = client.post("/api/whatsapp/webhook", json=_payload("491705550001"))
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ambiguous"
    finally:
        web_settings.whatsapp_bot_enabled = False
        web_settings.whatsapp_phone_number_id = ""
