"""Rollen-Matrix des WhatsApp-Bots (owner > manager > cleaner)."""

from __future__ import annotations

from backend.features.whatsapp_bot.models import BotAction, BotRole

# Welche Rollen dürfen welche Aktion ausführen (Spec: docs/WHATSAPP_BOT_SPEC.md).
# Regel: Ändern darf ausschließlich der Owner. Manager dürfen lesen und planen,
# Reinigungskräfte ausschließlich ihre eigenen Putztermine abrufen.
_READ = frozenset({"owner", "manager"})
_WRITE = frozenset({"owner"})
_ALL = frozenset({"owner", "manager", "cleaner"})

_MATRIX: dict[BotAction, frozenset[str]] = {
    BotAction.PUTZPLAN_ERSTELLEN: _READ,
    BotAction.PUTZPLAN_EIGENER_ABRUF: _ALL,
    BotAction.BUCHUNGEN_ANZEIGEN: _READ,
    BotAction.BUCHUNG_DETAILS: _READ,
    BotAction.MITARBEITER_LISTE: _READ,
    BotAction.OBJEKT_LISTE: _READ,
    BotAction.REVIEW_UEBERSICHT: _READ,
    BotAction.REVIEW_LISTE: _READ,
    BotAction.REVIEW_DETAILS: _READ,
    # Freigeben löst Benachrichtigungen aus → wie jede Schreibaktion Owner-only.
    BotAction.REVIEW_FREIGEBEN: _WRITE,
    BotAction.REVIEW_ALLE_FREIGEBEN: _WRITE,
    BotAction.MITARBEITER_ANLEGEN: _WRITE,
    BotAction.MITARBEITER_BEARBEITEN: _WRITE,
    BotAction.MITARBEITER_AENDERN: _WRITE,
    BotAction.OBJEKT_ANLEGEN: _WRITE,
    BotAction.OBJEKT_ZUWEISEN: _WRITE,
    BotAction.OBJEKT_ENTZIEHEN: _WRITE,
    BotAction.OBJEKT_BEARBEITEN: _WRITE,
    BotAction.OBJEKT_LOESCHEN: _WRITE,
    BotAction.HILFE: _ALL,
    BotAction.UNKLAR: _ALL,
}


def is_allowed(role: BotRole, action: BotAction) -> bool:
    """True wenn die Rolle die Aktion ausführen darf."""
    return role in _MATRIX.get(action, frozenset())
