"""Kern des WhatsApp-Bots: Parsing, Routing, Bestätigungen, Audit."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from backend.features.whatsapp_bot import (
    handlers_admin,
    handlers_edit,
    handlers_read,
    handlers_review,
    messages,
)
from backend.features.whatsapp_bot.deps import BotDeps, HandlerResult
from backend.features.whatsapp_bot.intent_service import IntentService
from backend.features.whatsapp_bot.messenger import BotMessenger, deliver_reply
from backend.features.whatsapp_bot.models import (
    BotAction,
    BotReply,
    PendingAction,
    ResolvedSender,
    UserIntent,
    parse_button_id,
)
from backend.features.whatsapp_bot.permissions import is_allowed
from backend.features.whatsapp_bot.sender_resolver import SenderResolver
from backend.features.whatsapp_bot.transcription import Transcriber

logger = logging.getLogger(__name__)

Handler = Callable[[BotDeps, ResolvedSender, UserIntent], HandlerResult]

_HANDLERS: dict[BotAction, Handler] = {
    BotAction.PUTZPLAN_ERSTELLEN: handlers_read.handle_putzplan,
    BotAction.PUTZPLAN_EIGENER_ABRUF: handlers_read.handle_putzplan_eigene,
    BotAction.BUCHUNGEN_ANZEIGEN: handlers_read.handle_buchungen,
    BotAction.BUCHUNG_DETAILS: handlers_read.handle_buchung_details,
    BotAction.MITARBEITER_LISTE: handlers_admin.handle_mitarbeiter_liste,
    BotAction.MITARBEITER_ANLEGEN: handlers_admin.handle_mitarbeiter_anlegen,
    BotAction.MITARBEITER_BEARBEITEN: handlers_admin.handle_mitarbeiter_bearbeiten,
    BotAction.MITARBEITER_AENDERN: handlers_edit.handle_mitarbeiter_aendern,
    BotAction.OBJEKT_LISTE: handlers_admin.handle_objekt_liste,
    BotAction.OBJEKT_ANLEGEN: handlers_admin.handle_objekt_anlegen,
    BotAction.OBJEKT_ZUWEISEN: handlers_admin.handle_objekt_zuweisen,
    BotAction.OBJEKT_ENTZIEHEN: handlers_edit.handle_objekt_entziehen,
    BotAction.OBJEKT_BEARBEITEN: handlers_edit.handle_objekt_bearbeiten,
    BotAction.OBJEKT_LOESCHEN: handlers_edit.handle_objekt_loeschen,
    BotAction.REVIEW_UEBERSICHT: handlers_review.handle_review_uebersicht,
    BotAction.REVIEW_LISTE: handlers_review.handle_review_liste,
    BotAction.REVIEW_DETAILS: handlers_review.handle_review_details,
    BotAction.REVIEW_NACHRICHT: handlers_review.handle_review_nachricht,
    BotAction.REVIEW_FREIGEBEN: handlers_review.handle_review_freigeben,
    BotAction.REVIEW_ALLE_FREIGEBEN: handlers_review.handle_review_alle_freigeben,
}


def _execute_pending(
    deps: BotDeps, sender: ResolvedSender, pending: PendingAction
) -> BotReply:
    """Routet eine bestätigte Schreiboperation ans zuständige Modul."""
    if pending.action in handlers_edit.EDIT_ACTIONS:
        return handlers_edit.execute_pending(deps, sender, pending)
    if pending.action in handlers_review.REVIEW_ACTIONS:
        return handlers_review.execute_pending(deps, sender, pending)
    return handlers_admin.execute_pending(deps, sender, pending)


@dataclass
class IncomingMessage:
    """Normalisierte eingehende Nachricht aus dem Meta-Payload."""

    wa_id: str
    sender_name: str
    message_id: str
    kind: str  # text | audio | button
    text: str = ""
    button_id: str = ""
    media_id: str = ""
    mime_type: str = ""


def parse_incoming(payload: dict[str, Any]) -> IncomingMessage | None:
    """Extrahiert die erste Nachricht aus einem Meta-Webhook-Payload."""
    try:
        value = payload["entry"][0]["changes"][0]["value"]
    except (KeyError, IndexError, TypeError):
        return None
    msgs = value.get("messages") or []
    if not msgs:
        return None  # Status-Updates etc.
    msg = msgs[0]
    wa_id = str(msg.get("from", "")).strip()
    if not wa_id:
        return None
    contacts = value.get("contacts") or []
    name = contacts[0].get("profile", {}).get("name", wa_id) if contacts else wa_id
    base = IncomingMessage(
        wa_id=wa_id,
        sender_name=str(name),
        message_id=str(msg.get("id", "")),
        kind="",
    )
    msg_type = msg.get("type")
    if msg_type == "text":
        base.kind = "text"
        base.text = str(msg.get("text", {}).get("body", "")).strip()
        return base if base.text else None
    if msg_type == "audio":
        audio = msg.get("audio", {})
        base.kind = "audio"
        base.media_id = str(audio.get("id", ""))
        base.mime_type = str(audio.get("mime_type", "audio/ogg"))
        return base if base.media_id else None
    if msg_type == "interactive":
        interactive = msg.get("interactive", {})
        reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
        base.kind = "button"
        base.button_id = str(reply.get("id", ""))
        return base if base.button_id else None
    return None


class WhatsAppBotService:
    """Verarbeitet eingehende Nachrichten und antwortet über den Messenger."""

    def __init__(
        self,
        *,
        deps: BotDeps,
        resolver: SenderResolver,
        intent_service: IntentService,
        messenger: BotMessenger,
        transcriber: Transcriber | None = None,
        media_download: Callable[[str], bytes | None] | None = None,
    ) -> None:
        """Initialize with wired dependencies (alle mockbar)."""
        self._deps = deps
        self._resolver = resolver
        self._intent = intent_service
        self._messenger = messenger
        self._transcriber = transcriber
        self._media_download = media_download

    def handle(self, payload: dict[str, Any], account_id: str) -> str:
        """Verarbeitet einen Webhook-Payload; gibt einen Status-Slug zurück."""
        incoming = parse_incoming(payload)
        if incoming is None:
            return "ignored"

        sender = self._resolver.resolve(incoming.wa_id, account_id=account_id)
        if sender is None:
            self._messenger.send_text(incoming.wa_id, messages.unknown_number())
            return "unknown_sender"

        if not self._deps.conversation_repo.mark_message_processed(
            account_id=account_id,
            wa_id=sender.wa_id,
            message_id=incoming.message_id,
        ):
            return "duplicate"

        try:
            reply = self._dispatch(incoming, sender)
        except Exception:
            logger.exception("WhatsApp-Bot: Verarbeitung fehlgeschlagen")
            reply = BotReply.message(messages.error_generic())
        deliver_reply(self._messenger, sender.wa_id, reply)
        return "handled"

    def _dispatch(self, incoming: IncomingMessage, sender: ResolvedSender) -> BotReply:
        if incoming.kind == "button":
            return self._handle_button(incoming, sender)
        text = incoming.text
        if incoming.kind == "audio":
            text = self._transcribe(incoming) or ""
            if not text:
                return BotReply.message(
                    messages.clarification(
                        "Ich konnte die Sprachnachricht nicht verstehen. "
                        "Schreib mir bitte kurz, worum es geht."
                    )
                )
        return self._handle_text(text, sender)

    def _handle_text(self, text: str, sender: ResolvedSender) -> BotReply:
        known = [
            p.name
            for p in self._deps.property_repo.list_all(account_id=sender.account_id)
            if p.name
        ]
        intent = self._intent.parse(
            text, known_properties=known, timezone=self._deps.timezone
        )
        action = self._effective_action(intent.action, sender)
        self._deps.audit_repo.append(
            account_id=sender.account_id,
            wa_id=sender.wa_id,
            action=action.value,
            payload={"text": text[:500]},
        )
        if action == BotAction.HILFE:
            return BotReply.message(messages.welcome(sender.name, sender.role))
        if action == BotAction.UNKLAR:
            return BotReply.message(
                messages.clarification(
                    "Das habe ich nicht verstanden. "
                    'Schreib z. B. _"Putzplan für nächste Woche"_ oder _"Hilfe"_.'
                )
            )
        if not is_allowed(sender.role, action):
            return BotReply.message(messages.permission_denied())
        handler = _HANDLERS.get(action)
        if handler is None:
            return BotReply.message(messages.error_generic())
        intent.action = action
        result = handler(self._deps, sender, intent)
        if result.pending is not None:
            self._deps.conversation_repo.set_pending_action(
                account_id=sender.account_id,
                wa_id=sender.wa_id,
                action=result.pending.to_mongo(),
            )
        return result.reply

    def _handle_button(
        self, incoming: IncomingMessage, sender: ResolvedSender
    ) -> BotReply:
        parsed = parse_button_id(incoming.button_id)
        pending_doc = self._deps.conversation_repo.get_pending_action(
            account_id=sender.account_id, wa_id=sender.wa_id
        )
        pending = PendingAction.from_mongo(pending_doc) if pending_doc else None
        if parsed is None or pending is None or parsed[1] != pending.action_id:
            return BotReply.message(
                messages.clarification(
                    "Diese Aktion ist nicht mehr gültig. Bitte starte neu."
                )
            )
        verb, _action_id = parsed
        self._deps.conversation_repo.set_pending_action(
            account_id=sender.account_id, wa_id=sender.wa_id, action=None
        )
        if verb == "cancel":
            self._deps.audit_repo.append(
                account_id=sender.account_id,
                wa_id=sender.wa_id,
                action=f"{pending.action.value}_cancelled",
                payload=pending.payload,
            )
            return BotReply.message(messages.action_cancelled())
        if not is_allowed(sender.role, pending.action):
            return BotReply.message(messages.permission_denied())
        reply = _execute_pending(self._deps, sender, pending)
        self._deps.audit_repo.append(
            account_id=sender.account_id,
            wa_id=sender.wa_id,
            action=pending.action.value,
            payload=pending.payload,
            confirmed=True,
        )
        return reply

    def _transcribe(self, incoming: IncomingMessage) -> str | None:
        if self._transcriber is None or self._media_download is None:
            return None
        audio = self._media_download(incoming.media_id)
        if not audio:
            return None
        return self._transcriber.transcribe(audio, mime_type=incoming.mime_type)

    @staticmethod
    def _effective_action(action: BotAction, sender: ResolvedSender) -> BotAction:
        """Reinigungskräfte sehen bei Putzplan-Anfragen nur eigene Termine."""
        if sender.role == "cleaner" and action == BotAction.PUTZPLAN_ERSTELLEN:
            return BotAction.PUTZPLAN_EIGENER_ABRUF
        return action
