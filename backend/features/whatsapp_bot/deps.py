"""Gemeinsame Abhängigkeiten und Ergebnistypen der Bot-Handler."""

from __future__ import annotations

from dataclasses import dataclass

from backend.features.whatsapp_bot.models import BotReply, PendingAction
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
from backend.infrastructure.repositories.whatsapp_audit_repository import (
    WhatsAppAuditRepository,
)
from backend.infrastructure.repositories.whatsapp_conversation_repository import (
    WhatsAppConversationRepository,
)


@dataclass
class BotDeps:
    """Repositories, auf denen die Handler arbeiten (alle tenant-scoped)."""

    cleaning_task_repo: CleaningTaskRepository
    cleaning_partner_repo: CleaningPartnerRepository
    property_repo: PropertyRepository
    extraction_repo: ExtractionRepository
    conversation_repo: WhatsAppConversationRepository
    audit_repo: WhatsAppAuditRepository
    timezone: str = "Europe/Berlin"


@dataclass
class HandlerResult:
    """Antwort eines Handlers, optional mit wartender Bestätigung."""

    reply: BotReply
    pending: PendingAction | None = None
