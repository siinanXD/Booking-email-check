"""Tests: WhatsApp Echo-Bot (Schritt 1) und Webhook-Verifizierung."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from backend.core.config.settings import Settings
from backend.features.notifications.whatsapp_echo_service import WhatsAppEchoService


class _SpySender:
    def __init__(self, result: bool = True) -> None:
        self.result = result
        self.calls: list[tuple[str, str]] = []

    def send_text(self, recipient_wa_id: str, text: str) -> bool:
        self.calls.append((recipient_wa_id, text))
        return self.result


def _meta_payload(text: str = "Hallo Bot", sender: str = "4915712345678") -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "111222333"},
                            "contacts": [{"profile": {"name": "Max"}}],
                            "messages": [
                                {
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


def _echo_settings() -> Settings:
    return Settings.model_validate(
        {
            "OPENAI_API_KEY": "sk-test",
            "MONGODB_URI": "mongodb://localhost",
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test",
            "LLM_MODE": "mock",
        }
    )


def test_echo_service_sends_echo_to_sender() -> None:
    spy = _SpySender()
    svc = WhatsAppEchoService(_echo_settings(), sender=spy)
    assert svc.handle(_meta_payload("Test 123")) is True
    assert len(spy.calls) == 1
    recipient, text = spy.calls[0]
    assert recipient == "4915712345678"
    assert "Test 123" in text
    assert "Max" in text


def test_echo_service_ignores_non_text_payload() -> None:
    spy = _SpySender()
    svc = WhatsAppEchoService(_echo_settings(), sender=spy)
    payload = _meta_payload()
    payload["entry"][0]["changes"][0]["value"]["messages"][0]["type"] = "image"
    assert svc.handle(payload) is False
    assert spy.calls == []


def test_echo_service_ignores_status_updates() -> None:
    spy = _SpySender()
    svc = WhatsAppEchoService(_echo_settings(), sender=spy)
    payload = _meta_payload()
    del payload["entry"][0]["changes"][0]["value"]["messages"]
    assert svc.handle(payload) is False
    assert spy.calls == []


def test_webhook_echo_mode_replies_to_sender(
    client: Any, web_settings: Settings
) -> None:
    web_settings.whatsapp_echo_mode = True
    try:
        with patch(
            "backend.features.notifications.whatsapp_echo_service"
            ".MetaTextSender.send_text",
            return_value=True,
        ) as send_mock:
            resp = client.post("/api/whatsapp/webhook", json=_meta_payload("Ping"))
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "echoed"
        recipient, text = send_mock.call_args.args
        assert recipient == "4915712345678"
        assert "Ping" in text
    finally:
        web_settings.whatsapp_echo_mode = False


def test_webhook_without_echo_mode_uses_forwarding_path(client: Any) -> None:
    resp = client.post("/api/whatsapp/webhook", json=_meta_payload())
    assert resp.status_code == 200
    # Kein Account für die phone_number_id hinterlegt → no_account
    assert resp.get_json()["status"] == "no_account"


def test_webhook_get_verification_returns_challenge(
    client: Any, web_settings: Settings
) -> None:
    web_settings.whatsapp_webhook_verify_token = "verify-me"
    try:
        resp = client.get(
            "/api/whatsapp/webhook",
            query_string={
                "hub.mode": "subscribe",
                "hub.verify_token": "verify-me",
                "hub.challenge": "12345",
            },
        )
        assert resp.status_code == 200
        assert resp.get_data(as_text=True) == "12345"
    finally:
        web_settings.whatsapp_webhook_verify_token = ""


def test_webhook_get_verification_rejects_wrong_token(
    client: Any, web_settings: Settings
) -> None:
    web_settings.whatsapp_webhook_verify_token = "verify-me"
    try:
        resp = client.get(
            "/api/whatsapp/webhook",
            query_string={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong",
                "hub.challenge": "12345",
            },
        )
        assert resp.status_code == 403
    finally:
        web_settings.whatsapp_webhook_verify_token = ""
