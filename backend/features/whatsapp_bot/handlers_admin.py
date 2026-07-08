"""Schreib-Handler: Mitarbeiter- und Objektverwaltung mit Bestätigung.

Keine Schreiboperation ohne expliziten Bestätigungs-Button. Die Handler
erzeugen nur PendingActions; ausgeführt wird erst in execute_pending().
"""

from __future__ import annotations

import uuid

from backend.core.models.entities import Property
from backend.features.cleaning.models import CleaningPartner
from backend.features.whatsapp_bot import messages
from backend.features.whatsapp_bot.deps import BotDeps, HandlerResult
from backend.features.whatsapp_bot.models import (
    BotAction,
    BotButton,
    BotReply,
    PendingAction,
    ResolvedSender,
    UserIntent,
)


def _confirm_buttons(action_id: str) -> list[BotButton]:
    return [
        BotButton(id=f"confirm_{action_id}", title="\u2705 Bestätigen"),
        BotButton(id=f"cancel_{action_id}", title="\u274c Abbrechen"),
    ]


def _normalize_phone(raw: str) -> str:
    digits = "".join(ch for ch in raw if ch.isdigit())
    return f"+{digits}" if digits else ""


def handle_mitarbeiter_liste(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Alle Mitarbeiter (Putzpartner) des Mandanten."""
    partners = deps.cleaning_partner_repo.list_partners(account_id=sender.account_id)
    return HandlerResult(reply=BotReply.message(messages.employee_list(partners)))


def handle_mitarbeiter_anlegen(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Neuen Mitarbeiter vorbereiten — Anlage erst nach Bestätigung."""
    name = (intent.person_name or "").strip()
    phone = _normalize_phone(intent.person_phone or "")
    if not name or not phone:
        missing = (
            "Name und Telefonnummer"
            if not name and not phone
            else ("die Telefonnummer" if not phone else "den Namen")
        )
        return HandlerResult(
            reply=BotReply.message(
                messages.clarification(
                    f"Um einen Mitarbeiter anzulegen, brauche ich noch {missing}."
                )
            )
        )
    properties = [intent.property_name] if intent.property_name else []
    pending = PendingAction(
        action_id=uuid.uuid4().hex,
        action=BotAction.MITARBEITER_ANLEGEN,
        payload={"name": name, "phone": phone, "properties": properties},
    )
    reply = BotReply(
        text=messages.employee_confirm(name, phone, properties),
        buttons=_confirm_buttons(pending.action_id),
    )
    return HandlerResult(reply=reply, pending=pending)


def handle_mitarbeiter_bearbeiten(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Mitarbeiter deaktivieren (Soft-Delete) — erst nach Bestätigung."""
    name = (intent.person_name or "").strip()
    if not name:
        return HandlerResult(
            reply=BotReply.message(
                messages.clarification("Welchen Mitarbeiter meinst du?")
            )
        )
    partner = _find_partner_by_name(deps, sender.account_id, name)
    if partner is None:
        return HandlerResult(
            reply=BotReply.message(
                messages.clarification(f"Ich kenne keinen Mitarbeiter *{name}*.")
            )
        )
    pending = PendingAction(
        action_id=uuid.uuid4().hex,
        action=BotAction.MITARBEITER_BEARBEITEN,
        payload={"partner_id": partner.partner_id, "name": partner.name},
    )
    reply = BotReply(
        text=messages.employee_deactivate_confirm(partner.name),
        buttons=_confirm_buttons(pending.action_id),
    )
    return HandlerResult(reply=reply, pending=pending)


def handle_objekt_liste(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Alle Objekte des Mandanten."""
    props = deps.property_repo.list_all(account_id=sender.account_id)
    names = sorted({p.name for p in props if p.name})
    return HandlerResult(reply=BotReply.message(messages.property_list(names)))


def handle_objekt_anlegen(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Neues Objekt vorbereiten — Anlage erst nach Bestätigung."""
    name = (intent.property_name or "").strip()
    if not name:
        return HandlerResult(
            reply=BotReply.message(
                messages.clarification("Wie soll das neue Objekt heißen?")
            )
        )
    pending = PendingAction(
        action_id=uuid.uuid4().hex,
        action=BotAction.OBJEKT_ANLEGEN,
        payload={"name": name},
    )
    reply = BotReply(
        text=messages.property_confirm(name),
        buttons=_confirm_buttons(pending.action_id),
    )
    return HandlerResult(reply=reply, pending=pending)


def handle_objekt_zuweisen(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Objekt einem Mitarbeiter zuordnen — erst nach Bestätigung."""
    name = (intent.person_name or "").strip()
    prop = (intent.property_name or "").strip()
    if not name or not prop:
        return HandlerResult(
            reply=BotReply.message(
                messages.clarification(
                    "Wen soll ich welchem Objekt zuordnen? "
                    "Bitte nenn mir Mitarbeiter und Objekt."
                )
            )
        )
    partner = _find_partner_by_name(deps, sender.account_id, name)
    if partner is None:
        return HandlerResult(
            reply=BotReply.message(
                messages.clarification(f"Ich kenne keinen Mitarbeiter *{name}*.")
            )
        )
    pending = PendingAction(
        action_id=uuid.uuid4().hex,
        action=BotAction.OBJEKT_ZUWEISEN,
        payload={
            "partner_id": partner.partner_id,
            "partner_name": partner.name,
            "property_name": prop,
        },
    )
    reply = BotReply(
        text=messages.property_assign_confirm(partner.name, prop),
        buttons=_confirm_buttons(pending.action_id),
    )
    return HandlerResult(reply=reply, pending=pending)


def execute_pending(
    deps: BotDeps, sender: ResolvedSender, pending: PendingAction
) -> BotReply:
    """Führt eine bestätigte Schreiboperation aus (deterministisch)."""
    payload = pending.payload
    if pending.action == BotAction.MITARBEITER_ANLEGEN:
        partner = CleaningPartner(
            partner_id=uuid.uuid4().hex,
            account_id=sender.account_id,
            name=str(payload.get("name", "")),
            phone=str(payload.get("phone", "")) or None,
            property_names=[str(p) for p in payload.get("properties", []) if p],
        )
        deps.cleaning_partner_repo.upsert(partner, account_id=sender.account_id)
        return BotReply.message(
            messages.action_confirmed(f"Mitarbeiter *{partner.name}* angelegt.")
        )
    if pending.action == BotAction.MITARBEITER_BEARBEITEN:
        ok = deps.cleaning_partner_repo.deactivate(
            str(payload.get("partner_id", "")), account_id=sender.account_id
        )
        name = str(payload.get("name", ""))
        if not ok:
            return BotReply.message(messages.error_generic())
        return BotReply.message(
            messages.action_confirmed(f"Mitarbeiter *{name}* deaktiviert.")
        )
    if pending.action == BotAction.OBJEKT_ANLEGEN:
        name = str(payload.get("name", ""))
        prop = Property(
            property_id=uuid.uuid4().hex,
            name=name,
            account_id=sender.account_id,
        )
        deps.property_repo.upsert(prop, account_id=sender.account_id)
        return BotReply.message(messages.action_confirmed(f"Objekt *{name}* angelegt."))
    if pending.action == BotAction.OBJEKT_ZUWEISEN:
        assignee = deps.cleaning_partner_repo.get(
            str(payload.get("partner_id", "")), account_id=sender.account_id
        )
        prop_name = str(payload.get("property_name", ""))
        if assignee is None:
            return BotReply.message(messages.error_generic())
        if prop_name not in assignee.property_names:
            assignee.property_names.append(prop_name)
            deps.cleaning_partner_repo.upsert(assignee, account_id=sender.account_id)
        return BotReply.message(
            messages.action_confirmed(
                f"*{prop_name}* ist jetzt *{assignee.name}* zugeordnet."
            )
        )
    return BotReply.message(messages.error_generic())


def _find_partner_by_name(
    deps: BotDeps, account_id: str, name: str
) -> CleaningPartner | None:
    key = name.strip().lower()
    for partner in deps.cleaning_partner_repo.list_partners(account_id=account_id):
        if partner.name.strip().lower() == key:
            return partner
    return None
