"""Verdrahtung des WhatsApp-Bots aus AppContext + effektiven Settings."""

from __future__ import annotations

from typing import Any

from backend.core.config.settings import Settings
from backend.features.platform.effective_settings import merge_platform_settings
from backend.features.whatsapp_bot.deps import BotDeps
from backend.features.whatsapp_bot.intent_service import IntentService
from backend.features.whatsapp_bot.messenger import MetaBotMessenger
from backend.features.whatsapp_bot.sender_resolver import SenderResolver
from backend.features.whatsapp_bot.service import WhatsAppBotService
from backend.features.whatsapp_bot.transcription import (
    Transcriber,
    WhisperTranscriber,
)
from backend.infrastructure.repositories.property_repository import PropertyRepository
from backend.infrastructure.repositories.whatsapp_audit_repository import (
    WhatsAppAuditRepository,
)
from backend.infrastructure.repositories.whatsapp_conversation_repository import (
    WhatsAppConversationRepository,
)

# Repos je Db-Instanz cachen, damit Indexe nicht pro Request angelegt werden.
_repo_cache: dict[int, tuple[Any, Any, Any]] = {}


def _repos_for(db: Any) -> tuple[Any, Any, Any]:
    key = id(db)
    if key not in _repo_cache:
        _repo_cache[key] = (
            PropertyRepository(db),
            WhatsAppConversationRepository(db),
            WhatsAppAuditRepository(db),
        )
    return _repo_cache[key]


def build_bot_service(
    ctx: Any,
    settings: Settings,
    *,
    account_id: str,
) -> WhatsAppBotService:
    """Baut den Bot-Service mit Mandanten-Credentials (DB überschreibt .env)."""
    platform = ctx.platform_settings_repo.get(account_id)
    effective = merge_platform_settings(settings, platform)

    property_repo, conversation_repo, audit_repo = _repos_for(ctx.db)
    deps = BotDeps(
        cleaning_task_repo=ctx.cleaning_task_repo,
        cleaning_partner_repo=ctx.cleaning_partner_repo,
        property_repo=property_repo,
        extraction_repo=ctx.extraction_repo,
        conversation_repo=conversation_repo,
        audit_repo=audit_repo,
    )
    messenger = MetaBotMessenger(
        access_token=effective.whatsapp_access_token,
        phone_number_id=effective.whatsapp_phone_number_id,
        api_version=effective.whatsapp_api_version,
    )
    transcriber: Transcriber | None = None
    if settings.llm_mode != "mock" and settings.openai_api_key:
        transcriber = WhisperTranscriber(settings.openai_api_key)

    return WhatsAppBotService(
        deps=deps,
        resolver=SenderResolver(ctx.user_repo, ctx.cleaning_partner_repo),
        intent_service=IntentService(ctx.llm, settings.whatsapp_bot_intent_model),
        messenger=messenger,
        transcriber=transcriber,
        media_download=messenger.download_media,
    )
