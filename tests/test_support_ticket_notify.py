"""Support-Ticket WhatsApp-Benachrichtigung."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.core.config.settings import Settings
from backend.core.models.support_ticket import SupportTicketRecord
from backend.features.support.support_ticket_notify_service import (
    SupportTicketNotifyService,
)
from backend.infrastructure.repositories.platform_admin_config_repository import (
    PlatformAdminConfigRecord,
    PlatformAdminConfigRepository,
)
from tests.mocks import MockWhatsAppClient


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "OPENAI_API_KEY": "test",
        "MONGODB_URI": "mongodb://localhost:27017",
        "LANGFUSE_PUBLIC_KEY": "pk-test",
        "LANGFUSE_SECRET_KEY": "sk-test",
        "WHATSAPP_ENABLED": True,
        "WHATSAPP_ACCESS_TOKEN": "token",
        "WHATSAPP_PHONE_NUMBER_ID": "123456789012345",
    }
    base.update(overrides)
    return Settings.model_validate(base)


def test_notify_uses_support_template(mock_db) -> None:
    repo = PlatformAdminConfigRepository(mock_db)
    repo.save(
        PlatformAdminConfigRecord(
            platform_admin_whatsapp_e164="+491701234567",
            whatsapp_template_support_ticket="platform_support_ticket_de",
        )
    )
    client = MockWhatsAppClient()
    svc = SupportTicketNotifyService(_settings(), repo, whatsapp_client=client)
    ticket = SupportTicketRecord(
        ticket_id="t1",
        account_id="acc1",
        created_by_user_id="u1",
        created_by_email="user@test.local",
        message="Hilfe\nbei Mail",
        urgency="high",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    status, error, msg_id = svc.notify_new_ticket(
        ticket, account_display_name="Test GmbH"
    )
    assert status == "sent"
    assert error is None
    assert msg_id is not None
    assert len(client.sent) == 1
    assert client.sent[0].template_name == "platform_support_ticket_de"
    assert client.sent[0].template_params[0] == "Test GmbH"
    assert client.sent[0].template_params[1] == "Hoch"
    assert client.sent[0].template_params[2] == "user@test.local"
    assert "\n" not in client.sent[0].template_params[3]


def test_notify_skipped_when_disabled(mock_db) -> None:
    repo = PlatformAdminConfigRepository(mock_db)
    client = MockWhatsAppClient()
    svc = SupportTicketNotifyService(
        _settings(WHATSAPP_ENABLED=False),
        repo,
        whatsapp_client=client,
    )
    ticket = SupportTicketRecord(
        ticket_id="t2",
        account_id="acc1",
        created_by_user_id="u1",
        created_by_email="user@test.local",
        message="Test",
        urgency="normal",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    status, _, _ = svc.notify_new_ticket(ticket, account_display_name="X")
    assert status == "skipped"
    assert client.sent == []
