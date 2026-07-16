"""Fixtures für WhatsApp-Bot-Tests (mongomock, Fakes für LLM/Messenger)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
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
from backend.infrastructure.repositories.review_repository import ReviewRepository
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


class FakeReviewRouter:
    """Zeichnet Freigaben auf, statt den LangGraph-Workflow fortzusetzen."""

    def __init__(self) -> None:
        self.approved: list[str] = []
        self.fail_on: set[str] = set()

    def approve_draft(
        self, correlation_id: str, approved_body: str | None = None
    ) -> dict[str, Any]:
        if correlation_id in self.fail_on:
            raise RuntimeError("boom")
        self.approved.append(correlation_id)
        return {}

    def reject_draft(
        self, correlation_id: str, reason: str | None = None
    ) -> dict[str, Any]:
        return {}


@pytest.fixture
def router() -> FakeReviewRouter:
    """Aufzeichnender Review-Router."""
    return FakeReviewRouter()


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
def review_deps(bot_deps: BotDeps, mock_db: Any, router: FakeReviewRouter) -> BotDeps:
    """Bot-Deps inklusive Review-Warteschlange und Router."""
    bot_deps.review_repo = ReviewRepository(mock_db)
    bot_deps.review_router = router  # type: ignore[assignment]
    return bot_deps


@pytest.fixture
def fake_messenger() -> FakeMessenger:
    """Aufzeichnender Messenger."""
    return FakeMessenger()


def seed_owner(user_repo: UserRepository, account_id: str, phone: str) -> None:
    """Dashboard-Owner mit hinterlegter WhatsApp-Nummer."""
    user = user_repo.create(
        "owner@test.local",
        "hash",
        account_id=account_id,
        role="owner",
        first_name="Olaf",
    )
    user_repo.update_whatsapp_profile(
        user.id, whatsapp_phone_e164=f"+{phone}", whatsapp_enabled=True
    )


def seed_manager(user_repo: UserRepository, account_id: str, phone: str) -> None:
    """Dashboard-Member → Bot-Rolle "manager"."""
    user = user_repo.create(
        "member@test.local",
        "hash",
        account_id=account_id,
        role="member",
        first_name="Mara",
    )
    user_repo.update_whatsapp_profile(
        user.id, whatsapp_phone_e164=f"+{phone}", whatsapp_enabled=True
    )


def seed_review(
    deps: BotDeps,
    mock_db: Any,
    account_id: str,
    *,
    correlation_id: str,
    intent: str,
    guest: str,
    property_name: str,
) -> None:
    """Wartender Review-Eintrag samt zugehöriger Extraktion."""
    assert deps.review_repo is not None
    deps.review_repo.upsert_pending(
        correlation_id=correlation_id,
        message_id=f"msg-{correlation_id}",
        draft_body=f"Guten Tag {guest}, vielen Dank für Ihre Buchung.",
        grounding_flag=False,
        intent=intent,
        account_id=account_id,
    )
    ExtractionRepository(mock_db).save(
        correlation_id,
        f"msg-{correlation_id}",
        BookingExtraction(
            guest_name=guest,
            property_name=property_name,
            check_in="2026-07-17",
            check_out="2026-07-18",
            booking_number=f"REF{correlation_id}",
            intent=BookingIntent(intent),
        ),
        account_id=account_id,
    )


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
