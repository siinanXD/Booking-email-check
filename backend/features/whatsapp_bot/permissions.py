"""Rollen-Matrix des WhatsApp-Bots (owner > manager > cleaner)."""

from __future__ import annotations

from backend.features.whatsapp_bot.models import BotAction, BotRole

# Welche Rollen dürfen welche Aktion ausführen (Spec: docs/WHATSAPP_BOT_SPEC.md).
_MATRIX: dict[BotAction, frozenset[str]] = {
    BotAction.PUTZPLAN_ERSTELLEN: frozenset({"owner", "manager"}),
    BotAction.PUTZPLAN_EIGENER_ABRUF: frozenset({"owner", "manager", "cleaner"}),
    BotAction.BUCHUNGEN_ANZEIGEN: frozenset({"owner", "manager"}),
    BotAction.BUCHUNG_DETAILS: frozenset({"owner", "manager"}),
    BotAction.MITARBEITER_ANLEGEN: frozenset({"owner"}),
    BotAction.MITARBEITER_BEARBEITEN: frozenset({"owner", "manager"}),
    BotAction.MITARBEITER_LISTE: frozenset({"owner", "manager"}),
    BotAction.OBJEKT_ANLEGEN: frozenset({"owner", "manager"}),
    BotAction.OBJEKT_LISTE: frozenset({"owner", "manager"}),
    BotAction.OBJEKT_ZUWEISEN: frozenset({"owner", "manager"}),
    BotAction.HILFE: frozenset({"owner", "manager", "cleaner"}),
    BotAction.UNKLAR: frozenset({"owner", "manager", "cleaner"}),
}


def is_allowed(role: BotRole, action: BotAction) -> bool:
    """True wenn die Rolle die Aktion ausführen darf."""
    return role in _MATRIX.get(action, frozenset())
