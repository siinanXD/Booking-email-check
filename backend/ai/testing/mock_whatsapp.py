"""WhatsApp-Mock für Tests (ohne HTTP)."""

from __future__ import annotations

from backend.core.models.notification import WhatsAppSendResult, WhatsAppTemplateMessage


class MockWhatsAppClient:
    """Test-Stub: zeichnet Versuche auf, ohne HTTP."""

    def __init__(self) -> None:
        self.sent: list[WhatsAppTemplateMessage] = []

    def send_template(self, message: WhatsAppTemplateMessage) -> WhatsAppSendResult:
        self.sent.append(message)
        return WhatsAppSendResult(
            success=True,
            provider_message_id=f"mock-{len(self.sent)}",
        )
