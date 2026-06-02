"""WhatsApp hello_world Verbindungstest."""

from __future__ import annotations

from config.settings import Settings
from services.whatsapp_client import MetaCloudWhatsAppClient


def test_send_hello_world_builds_meta_payload(monkeypatch) -> None:
    """hello_world nutzt Meta-Standardvorlage ohne Body-Parameter."""
    captured: dict = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"messages": [{"id": "wamid.test123"}]}

    def fake_post(url: str, **kwargs: object) -> FakeResponse:
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return FakeResponse()

    monkeypatch.setattr(
        "services.whatsapp_client.httpx.post",
        fake_post,
    )
    settings = Settings.model_validate(
        {
            "OPENAI_API_KEY": "test",
            "MONGODB_URI": "mongodb://localhost:27017",
            "LANGFUSE_PUBLIC_KEY": "pk",
            "LANGFUSE_SECRET_KEY": "sk",
            "WHATSAPP_ACCESS_TOKEN": "token",
            "WHATSAPP_PHONE_NUMBER_ID": "12345",
        }
    )
    client = MetaCloudWhatsAppClient(settings)
    result = client.send_hello_world("+491701234567")

    assert result.success is True
    assert result.provider_message_id == "wamid.test123"
    payload = captured["json"]
    assert payload["template"]["name"] == "hello_world"
    assert payload["template"]["language"] == {"code": "en_US"}
    assert "components" not in payload["template"]
    assert payload["to"] == "491701234567"
