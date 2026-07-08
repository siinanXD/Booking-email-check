"""Fixtures für WhatsApp-Bot-Tests (mongomock, Fakes für LLM/Messenger)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from backend.ai.services.llm_types import LLMCompletion
from backend.features.whatsapp_bot.deps import BotDeps
from backend.features.whatsapp_bot.intent_service import IntentService
from backend.features.whatsapp_bot.models import BotButton, BotDocument
from backend.features.whatsapp_bot.sender_resolver import SenderResolver
from backend.features.whatsapp_bot.service import WhatsAppBotService
from backend.infrastructure.repositories.cleaning_partner_repository import (
    CleaningPartnerRepository,
)
from backend.infrastructure.repositories.cleaning_task_repository import (
    CleaningTaskRepository,
)
from backend.infrastructure.repositories.extraction_repository import (
    ExtractionRepository,
)
from backend.infrastructure.repositories.property_repository import PropertyRepository
from backend.infrastructure.repositories.user_repository import UserRepository
from backend.infrastructure.repositories.whatsapp_audit_repository import (
    WhatsAppAuditRepository,
)
from backend.infrastructure.repositories.whatsapp_conversation_repository import (
    WhatsAppConversationRepository,
)


class FakeIntentLLM:
    """Gibt eine vorbereitete JSON-Antwort zurück."""

    def __init__(self, payload: dict[str, Any] | str | None = None) -> None:
        self.payload = payload
        self.prompts: list[str] = []

    def complete(
        self, prompt: str, model: str, *, temperature: float | None = None
    ) -> LLMCompletion:
        self.prompts.append(prompt)
        if isinstance(self.payload, str):
            text = self.payload
        else:
            text = json.dumps(self.payload or {"action": "unklar"})
        return LLMCompletion(text=text, prompt_tokens=1, completion_tokens=1)


class FakeMessenger:
    """Zeichnet alle ausgehenden Nachrichten auf."""

    def __init__(self) -> None:
        self.texts: list[tuple[str, str]] = []
        self.buttons: list[tuple[str, str, list[BotButton]]] = []
        self.documents: list[tuple[str, BotDocument]] = []

    def send_text(self, recipient_wa_id: str, text: str) -> bool:
        self.texts.append((recipient_wa_id, text))
        return True

    def send_buttons(
        self, recipient_wa_id: str, text: str, buttons: list[BotButton]
    ) -> bool:
        self.buttons.append((recipient_wa_id, text, buttons))
        return True

    def send_document(self, recipient_wa_id: str, document: BotDocument) -> bool:
        self.documents.append((recipient_wa_id, document))
        return True

    @property
    def all_texts(self) -> str:
        parts = [t for _, t in self.texts]
        parts += [t for _, t, _ in self.buttons]
        return "\n".join(parts)


@pytest.fixture
def bot_deps(mock_db: Any) -> BotDeps:
    """Alle Bot-Repositories über mongomock."""
    return BotDeps(
        cleaning_task_repo=CleaningTaskRepository(mock_db),
        cleaning_partner_repo=CleaningPartnerRepository(mock_db),
        property_repo=PropertyRepository(mock_db),
        extraction_repo=ExtractionRepository(mock_db),
        conversation_repo=WhatsAppConversationRepository(mock_db),
        audit_repo=WhatsAppAuditRepository(mock_db),
    )


@pytest.fixture
def user_repo(mock_db: Any) -> UserRepository:
    """UserRepository über mongomock."""
    return UserRepository(mock_db)


@pytest.fixture
def fake_messenger() -> FakeMessenger:
    """Aufzeichnender Messenger."""
    return FakeMessenger()


def make_bot(
    deps: BotDeps,
    user_repo: UserRepository,
    messenger: FakeMessenger,
    llm_payload: dict[str, Any] | str | None = None,
) -> WhatsAppBotService:
    """Baut einen Bot-Service mit Fakes."""
    return WhatsAppBotService(
        deps=deps,
        resolver=SenderResolver(user_repo, deps.cleaning_partner_repo),
        intent_service=IntentService(FakeIntentLLM(llm_payload), "test-model"),
        messenger=messenger,
    )


def meta_text_payload(
    text: str,
    *,
    sender: str = "4915711111111",
    message_id: str = "wamid.1",
    name: str = "Anna",
) -> dict[str, Any]:
    """Meta-Webhook-Payload für eine Textnachricht."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "111222333"},
                            "contacts": [{"profile": {"name": name}}],
                            "messages": [
                                {
                                    "id": message_id,
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


def meta_button_payload(
    button_id: str,
    *,
    sender: str = "4915711111111",
    message_id: str = "wamid.btn",
) -> dict[str, Any]:
    """Meta-Webhook-Payload für einen Button-Reply."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "111222333"},
                            "messages": [
                                {
                                    "id": message_id,
                                    "from": sender,
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {
                                            "id": button_id,
                                            "title": "x",
                                        },
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        ],
    }
