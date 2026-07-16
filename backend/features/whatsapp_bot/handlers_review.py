"""Review per Chat: Übersicht, Liste, Details, Freigabe.

Spiegelt die Review-Warteschlange des Dashboards. Freigeben verschickt keine
Mail an den Gast (den Pfad gibt es nicht), löst aber WhatsApp-Benachrichtigungen
an Host und Mitarbeiter aus — deshalb nie ohne Bestätigungs-Button.

Die Nummerierung bezieht sich immer auf die zuletzt gezeigte Liste
(conversation_repo.last_listing), nicht auf eine live neu sortierte
Warteschlange. Aufgelöst wird sie beim Befehl, nicht beim Klick: die
PendingAction trägt die correlation_id, damit eine zwischenzeitlich
eingetroffene Mail die Auswahl nicht verschiebt.
"""

from __future__ import annotations

import uuid

from backend.features.whatsapp_bot import messages_review
from backend.features.whatsapp_bot.deps import BotDeps, HandlerResult
from backend.features.whatsapp_bot.handlers_admin import _confirm_buttons
from backend.features.whatsapp_bot.models import (
    BotAction,
    BotReply,
    PendingAction,
    ResolvedSender,
    UserIntent,
)
from backend.features.whatsapp_bot.review_data import (
    ReviewEntry,
    load_entries,
    resolve_position,
    resolve_positions,
)

REVIEW_ACTIONS = frozenset(
    {BotAction.REVIEW_FREIGEBEN, BotAction.REVIEW_ALLE_FREIGEBEN}
)

_MAX_APPROVE_ALL = 20


def _unavailable() -> HandlerResult:
    return HandlerResult(reply=BotReply.message(messages_review.review_unavailable()))


def handle_review_uebersicht(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Wie viele Einträge warten, aufgeschlüsselt nach Intent."""
    if deps.review_repo is None:
        return _unavailable()
    entries = load_entries(deps, sender.account_id)
    return HandlerResult(reply=BotReply.message(messages_review.overview(entries)))


def handle_review_liste(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Nummerierte Liste; merkt sich die Reihenfolge für Folgebefehle."""
    if deps.review_repo is None:
        return _unavailable()
    entries = load_entries(deps, sender.account_id, intent_filter=intent.review_intent)
    deps.conversation_repo.set_last_listing(
        account_id=sender.account_id,
        wa_id=sender.wa_id,
        correlation_ids=[e.correlation_id for e in entries],
    )
    return HandlerResult(
        reply=BotReply.message(
            messages_review.listing(entries, intent_filter=intent.review_intent)
        )
    )


def handle_review_details(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Volle Karte eines Eintrags inklusive Antwortentwurf."""
    if deps.review_repo is None:
        return _unavailable()
    entry, error = resolve_position(deps, sender, intent)
    if entry is None:
        return HandlerResult(reply=BotReply.message(error or ""))
    return HandlerResult(reply=BotReply.message(messages_review.details(entry)))


def handle_review_nachricht(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Nur die Nachricht des Gastes im Wortlaut ("Nachricht zu Buchung 1")."""
    if deps.review_repo is None:
        return _unavailable()
    entry, error = resolve_position(deps, sender, intent)
    if entry is None:
        return HandlerResult(reply=BotReply.message(error or ""))
    return HandlerResult(reply=BotReply.message(messages_review.guest_message(entry)))


def handle_review_freigeben(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Einen oder mehrere Einträge freigeben — erst nach Bestätigung.

    "Buchung 1 und 3 freigeben" spart das einzelne Durchklicken. Aufgelöst wird
    beim Befehl, nicht beim Klick: die PendingAction trägt die correlation_ids,
    damit eine zwischenzeitlich eingetroffene Mail die Auswahl nicht verschiebt.
    """
    if deps.review_repo is None or deps.review_router is None:
        return _unavailable()
    entries, error = resolve_positions(deps, sender, intent)
    if not entries:
        return HandlerResult(reply=BotReply.message(error or ""))
    recipients = sorted(
        {name for entry in entries for name in _recipient_hint(deps, sender, entry)}
    )
    pending = PendingAction(
        action_id=uuid.uuid4().hex,
        action=BotAction.REVIEW_FREIGEBEN,
        payload={
            "correlation_ids": [e.correlation_id for e in entries],
            "label": _label(entries),
        },
    )
    text = (
        messages_review.approve_confirm(entries[0], recipients=recipients)
        if len(entries) == 1
        else messages_review.approve_selection_confirm(entries, recipients=recipients)
    )
    return HandlerResult(
        reply=BotReply(text=text, buttons=_confirm_buttons(pending.action_id)),
        pending=pending,
    )


def _label(entries: list[ReviewEntry]) -> str:
    """Audit-Bezeichnung: bei mehreren die Anzahl, sonst der Eintrag selbst."""
    if len(entries) == 1:
        return entries[0].short_label()
    return f"{len(entries)} Einträge"


def handle_review_alle_freigeben(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Sammelfreigabe der zuletzt gezeigten Liste — erst nach Bestätigung."""
    if deps.review_repo is None or deps.review_router is None:
        return _unavailable()
    entries = load_entries(deps, sender.account_id, intent_filter=intent.review_intent)
    if not entries:
        return HandlerResult(reply=BotReply.message(messages_review.nothing_pending()))
    if len(entries) > _MAX_APPROVE_ALL:
        return HandlerResult(
            reply=BotReply.message(messages_review.too_many(len(entries)))
        )
    partners = {
        name for entry in entries for name in _recipient_hint(deps, sender, entry)
    }
    pending = PendingAction(
        action_id=uuid.uuid4().hex,
        action=BotAction.REVIEW_ALLE_FREIGEBEN,
        payload={
            "correlation_ids": [e.correlation_id for e in entries],
            "label": f"{len(entries)} Einträge",
        },
    )
    reply = BotReply(
        text=messages_review.approve_all_confirm(entries, recipients=sorted(partners)),
        buttons=_confirm_buttons(pending.action_id),
    )
    return HandlerResult(reply=reply, pending=pending)


def _recipient_hint(
    deps: BotDeps, sender: ResolvedSender, entry: ReviewEntry
) -> list[str]:
    """Mitarbeiter, die bei Freigabe eine WhatsApp bekommen (nur Neubuchungen)."""
    if entry.intent != "new_booking" or not entry.property_name:
        return []
    partners = deps.cleaning_partner_repo.find_for_property(
        entry.property_name, account_id=sender.account_id
    )
    return [p.name for p in partners if p.phone and not p.test_mode]


def execute_pending(
    deps: BotDeps, sender: ResolvedSender, pending: PendingAction
) -> BotReply:
    """Führt eine bestätigte Freigabe aus."""
    router = deps.review_router
    if router is None:
        return BotReply.message(messages_review.review_unavailable())
    raw = pending.payload.get("correlation_ids")
    correlation_ids = [str(c) for c in raw] if isinstance(raw, list) else []
    done, failed = 0, 0
    for correlation_id in correlation_ids:
        try:
            router.approve_draft(correlation_id)
            done += 1
        except Exception:  # noqa: BLE001
            failed += 1
    return BotReply.message(messages_review.approved(done, failed))
