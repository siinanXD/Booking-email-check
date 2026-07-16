"""Änderungs-Handler: Felder ändern, umbenennen, löschen, Zuordnung lösen.

Ergänzt handlers_admin (anlegen/auflisten/zuweisen/deaktivieren). Auch hier
gilt: kein Schreibzugriff ohne Bestätigungs-Button, ausgeführt wird erst in
execute_pending().

Objekte werden nur archiviert (Soft-Delete), damit historische Buchungen und
Putzaufträge weiter auflösbar bleiben.
"""

from __future__ import annotations

import uuid

from backend.core.models.entities import Property
from backend.features.cleaning.models import CleaningPartner
from backend.features.whatsapp_bot import messages
from backend.features.whatsapp_bot.deps import BotDeps, HandlerResult
from backend.features.whatsapp_bot.handlers_admin import (
    _confirm_buttons,
    _find_partner_by_name,
    _normalize_phone,
)
from backend.features.whatsapp_bot.models import (
    BotAction,
    BotReply,
    PendingAction,
    ResolvedSender,
    UserIntent,
)

# Aktionen, die dieses Modul ausführt (Dispatch in service.py).
EDIT_ACTIONS = frozenset(
    {
        BotAction.MITARBEITER_AENDERN,
        BotAction.OBJEKT_BEARBEITEN,
        BotAction.OBJEKT_LOESCHEN,
        BotAction.OBJEKT_ENTZIEHEN,
    }
)


def _ask(question: str) -> HandlerResult:
    return HandlerResult(reply=BotReply.message(messages.clarification(question)))


def _find_property_by_name(
    deps: BotDeps, account_id: str, name: str
) -> Property | None:
    key = name.strip().lower()
    for prop in deps.property_repo.list_all(account_id=account_id):
        if prop.name.strip().lower() == key:
            return prop
    return None


def _partners_with_property(
    deps: BotDeps, account_id: str, property_name: str
) -> list[CleaningPartner]:
    key = property_name.strip().lower()
    return [
        partner
        for partner in deps.cleaning_partner_repo.list_partners(account_id=account_id)
        if any(name.strip().lower() == key for name in partner.property_names)
    ]


def handle_mitarbeiter_aendern(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Name und/oder Telefonnummer eines Mitarbeiters ändern."""
    name = (intent.person_name or "").strip()
    if not name:
        return _ask("Welchen Mitarbeiter soll ich ändern?")
    new_name = (intent.neuer_name or "").strip()
    new_phone = _normalize_phone(intent.person_phone or "")
    if not new_name and not new_phone:
        return _ask(
            f"Was soll ich bei *{name}* ändern — Name oder Telefonnummer? "
            'Z. B. _"Annas Nummer ist +4917012345678"_'
        )
    partner = _find_partner_by_name(deps, sender.account_id, name)
    if partner is None:
        return _ask(f"Ich kenne keinen Mitarbeiter *{name}*.")
    pending = PendingAction(
        action_id=uuid.uuid4().hex,
        action=BotAction.MITARBEITER_AENDERN,
        payload={
            "partner_id": partner.partner_id,
            "name": partner.name,
            "new_name": new_name or None,
            "new_phone": new_phone or None,
        },
    )
    reply = BotReply(
        text=messages.employee_update_confirm(
            partner.name, new_name=new_name or None, new_phone=new_phone or None
        ),
        buttons=_confirm_buttons(pending.action_id),
    )
    return HandlerResult(reply=reply, pending=pending)


def handle_objekt_bearbeiten(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Objekt umbenennen (Zuordnungen ziehen mit)."""
    old_name = (intent.property_name or "").strip()
    new_name = (intent.neuer_name or "").strip()
    if not old_name:
        return _ask("Welches Objekt soll ich umbenennen?")
    if not new_name:
        return _ask(f"Wie soll *{old_name}* künftig heißen?")
    prop = _find_property_by_name(deps, sender.account_id, old_name)
    if prop is None:
        return _ask(f"Ich kenne kein Objekt *{old_name}*.")
    affected = _partners_with_property(deps, sender.account_id, prop.name)
    pending = PendingAction(
        action_id=uuid.uuid4().hex,
        action=BotAction.OBJEKT_BEARBEITEN,
        payload={
            "property_id": prop.property_id,
            "old_name": prop.name,
            "new_name": new_name,
        },
    )
    reply = BotReply(
        text=messages.property_rename_confirm(
            prop.name, new_name, affected=len(affected)
        ),
        buttons=_confirm_buttons(pending.action_id),
    )
    return HandlerResult(reply=reply, pending=pending)


def handle_objekt_loeschen(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Objekt archivieren (Soft-Delete)."""
    name = (intent.property_name or "").strip()
    if not name:
        return _ask("Welches Objekt soll ich löschen?")
    prop = _find_property_by_name(deps, sender.account_id, name)
    if prop is None:
        return _ask(f"Ich kenne kein Objekt *{name}*.")
    affected = _partners_with_property(deps, sender.account_id, prop.name)
    pending = PendingAction(
        action_id=uuid.uuid4().hex,
        action=BotAction.OBJEKT_LOESCHEN,
        payload={"property_id": prop.property_id, "name": prop.name},
    )
    reply = BotReply(
        text=messages.property_delete_confirm(prop.name, affected=len(affected)),
        buttons=_confirm_buttons(pending.action_id),
    )
    return HandlerResult(reply=reply, pending=pending)


def handle_objekt_entziehen(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Zuordnung Objekt → Mitarbeiter lösen."""
    name = (intent.person_name or "").strip()
    prop_name = (intent.property_name or "").strip()
    if not name or not prop_name:
        return _ask(
            "Wem soll ich welches Objekt entziehen? "
            "Bitte nenn mir Mitarbeiter und Objekt."
        )
    partner = _find_partner_by_name(deps, sender.account_id, name)
    if partner is None:
        return _ask(f"Ich kenne keinen Mitarbeiter *{name}*.")
    key = prop_name.lower()
    if not any(p.strip().lower() == key for p in partner.property_names):
        return _ask(f"*{partner.name}* ist *{prop_name}* gar nicht zugeordnet.")
    pending = PendingAction(
        action_id=uuid.uuid4().hex,
        action=BotAction.OBJEKT_ENTZIEHEN,
        payload={
            "partner_id": partner.partner_id,
            "partner_name": partner.name,
            "property_name": prop_name,
        },
    )
    reply = BotReply(
        text=messages.property_unassign_confirm(partner.name, prop_name),
        buttons=_confirm_buttons(pending.action_id),
    )
    return HandlerResult(reply=reply, pending=pending)


def execute_pending(
    deps: BotDeps, sender: ResolvedSender, pending: PendingAction
) -> BotReply:
    """Führt eine bestätigte Änderung aus (deterministisch)."""
    payload = pending.payload
    account_id = sender.account_id
    if pending.action == BotAction.MITARBEITER_AENDERN:
        partner = deps.cleaning_partner_repo.get(
            str(payload.get("partner_id", "")), account_id=account_id
        )
        if partner is None:
            return BotReply.message(messages.error_generic())
        new_name = payload.get("new_name")
        new_phone = payload.get("new_phone")
        if new_name:
            partner.name = str(new_name)
        if new_phone:
            partner.phone = str(new_phone)
        deps.cleaning_partner_repo.upsert(partner, account_id=account_id)
        return BotReply.message(
            messages.action_confirmed(f"Mitarbeiter *{partner.name}* aktualisiert.")
        )
    if pending.action == BotAction.OBJEKT_BEARBEITEN:
        return _rename_property(deps, account_id, payload)
    if pending.action == BotAction.OBJEKT_LOESCHEN:
        name = str(payload.get("name", ""))
        ok = deps.property_repo.deactivate(
            str(payload.get("property_id", "")), account_id=account_id
        )
        if not ok:
            return BotReply.message(messages.error_generic())
        _detach_property(deps, account_id, name)
        return BotReply.message(messages.action_confirmed(f"Objekt *{name}* gelöscht."))
    if pending.action == BotAction.OBJEKT_ENTZIEHEN:
        partner = deps.cleaning_partner_repo.get(
            str(payload.get("partner_id", "")), account_id=account_id
        )
        prop_name = str(payload.get("property_name", ""))
        if partner is None:
            return BotReply.message(messages.error_generic())
        key = prop_name.strip().lower()
        partner.property_names = [
            p for p in partner.property_names if p.strip().lower() != key
        ]
        deps.cleaning_partner_repo.upsert(partner, account_id=account_id)
        return BotReply.message(
            messages.action_confirmed(
                f"*{prop_name}* ist *{partner.name}* nicht mehr zugeordnet."
            )
        )
    return BotReply.message(messages.error_generic())


def _rename_property(
    deps: BotDeps, account_id: str, payload: dict[str, object]
) -> BotReply:
    """Objekt umbenennen und alle Zuordnungen mitziehen."""
    prop = deps.property_repo.get_by_id(
        str(payload.get("property_id", "")), account_id=account_id
    )
    if prop is None:
        return BotReply.message(messages.error_generic())
    old_name = str(payload.get("old_name", ""))
    new_name = str(payload.get("new_name", ""))
    prop.name = new_name
    deps.property_repo.upsert(prop, account_id=account_id)
    key = old_name.strip().lower()
    for partner in _partners_with_property(deps, account_id, old_name):
        partner.property_names = [
            new_name if p.strip().lower() == key else p for p in partner.property_names
        ]
        deps.cleaning_partner_repo.upsert(partner, account_id=account_id)
    return BotReply.message(
        messages.action_confirmed(f"Objekt *{old_name}* heißt jetzt *{new_name}*.")
    )


def _detach_property(deps: BotDeps, account_id: str, name: str) -> None:
    """Entfernt ein archiviertes Objekt aus allen Mitarbeiter-Zuordnungen."""
    key = name.strip().lower()
    for partner in _partners_with_property(deps, account_id, name):
        partner.property_names = [
            p for p in partner.property_names if p.strip().lower() != key
        ]
        deps.cleaning_partner_repo.upsert(partner, account_id=account_id)
