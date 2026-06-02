"""Settings-API-Tests."""

from __future__ import annotations

from unittest.mock import patch

from models.notification import WhatsAppSendResult


def test_get_settings_requires_auth(client) -> None:
    resp = client.get("/api/settings")
    assert resp.status_code == 401


def test_get_and_update_settings(client, auth_headers) -> None:
    resp = client.get("/api/settings", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "whatsapp_enabled" in data
    assert "user_profile" in data

    resp = client.put(
        "/api/settings",
        headers=auth_headers,
        json={
            "whatsapp_enabled": True,
            "whatsapp_phone_number_id": "123456789012345",
            "user_profile": {
                "whatsapp_phone_e164": "+491701234567",
                "whatsapp_enabled": True,
            },
            "property_recipients": [
                {"property_name": "Apartment Mitte", "phones": ["+491709999999"]}
            ],
        },
    )
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated["whatsapp_enabled"] is True
    assert updated["whatsapp_phone_number_id"] == "123456789012345"
    assert updated["user_profile"]["whatsapp_phone_e164"] == "+491701234567"
    assert len(updated["property_recipients"]) == 1


def test_whatsapp_test_endpoint(client, auth_headers) -> None:
    with patch(
        "web.api.settings.send_whatsapp_hello_world_test",
        return_value=WhatsAppSendResult(success=True, provider_message_id="wamid.x"),
    ):
        resp = client.post(
            "/api/settings/whatsapp/test",
            headers=auth_headers,
            json={"recipient_e164": "+491701234567"},
        )
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True


def test_wipe_all_requires_confirmation(client, auth_headers) -> None:
    resp = client.post("/api/settings/wipe-all", headers=auth_headers, json={})
    assert resp.status_code == 400

    resp = client.post(
        "/api/settings/wipe-all",
        headers=auth_headers,
        json={"confirm": "ALLE DATEN LOESCHEN"},
    )
    assert resp.status_code == 200
    assert "deleted" in resp.get_json()
