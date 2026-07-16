"""Datenmodelle des WhatsApp-Bots (Intents, Sender, Antworten)."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

BotRole = Literal["owner", "manager", "cleaner"]


class BotAction(StrEnum):
    """Alle vom Bot unterstützten Aktionen."""

    PUTZPLAN_ERSTELLEN = "putzplan_erstellen"
    PUTZPLAN_EIGENER_ABRUF = "putzplan_eigener_abruf"
    BUCHUNGEN_ANZEIGEN = "buchungen_anzeigen"
    BUCHUNG_DETAILS = "buchung_details"
    MITARBEITER_ANLEGEN = "mitarbeiter_anlegen"
    # Deaktivieren (Soft-Delete). Feld-Änderungen: MITARBEITER_AENDERN.
    MITARBEITER_BEARBEITEN = "mitarbeiter_bearbeiten"
    MITARBEITER_AENDERN = "mitarbeiter_aendern"
    MITARBEITER_LISTE = "mitarbeiter_liste"
    OBJEKT_ANLEGEN = "objekt_anlegen"
    OBJEKT_LISTE = "objekt_liste"
    OBJEKT_ZUWEISEN = "objekt_zuweisen"
    OBJEKT_ENTZIEHEN = "objekt_entziehen"
    OBJEKT_BEARBEITEN = "objekt_bearbeiten"
    OBJEKT_LOESCHEN = "objekt_loeschen"
    HILFE = "hilfe"
    UNKLAR = "unklar"


class UserIntent(BaseModel):
    """Structured Output der Intent-Erkennung (LLM)."""

    action: BotAction = BotAction.UNKLAR
    zeitraum_start: date | None = None
    zeitraum_ende: date | None = None
    zeitraum_text: str | None = None
    person_name: str | None = None
    person_phone: str | None = None
    person_role: str | None = None
    property_name: str | None = None
    # Zielwert bei Umbenennungen; person_name/property_name bleiben der Ist-Wert.
    neuer_name: str | None = None
    booking_ref: str | None = None
    freitext: str | None = None


class ResolvedSender(BaseModel):
    """Aufgelöster Absender: Mandant + Rolle über die WhatsApp-Nummer."""

    account_id: str
    wa_id: str
    name: str
    role: BotRole
    partner_id: str | None = None  # gesetzt wenn role == "cleaner"


class BotButton(BaseModel):
    """Interactive Reply-Button (Meta-Limit: 3 Buttons, Titel 20 Zeichen)."""

    id: str
    title: str


class BotDocument(BaseModel):
    """Dokument-Anhang (z. B. Putzplan-Excel)."""

    filename: str
    content: bytes
    mime_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class BotReply(BaseModel):
    """Eine ausgehende Bot-Antwort (Text, optional Buttons/Dokument)."""

    text: str
    buttons: list[BotButton] = Field(default_factory=list)
    document: BotDocument | None = None

    @classmethod
    def message(cls, text: str) -> BotReply:
        """Einfache Textantwort."""
        return cls(text=text)


class PendingAction(BaseModel):
    """Wartende Schreiboperation, die per Button bestätigt werden muss."""

    action_id: str
    action: BotAction
    payload: dict[str, Any] = Field(default_factory=dict)

    def to_mongo(self) -> dict[str, Any]:
        """Serialisiert für die Conversations-Collection."""
        return {
            "action_id": self.action_id,
            "action": self.action.value,
            "payload": self.payload,
        }

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> PendingAction | None:
        """Deserialisiert; None bei unbekannter Aktion (defensiv)."""
        try:
            return cls(
                action_id=str(doc.get("action_id", "")),
                action=BotAction(str(doc.get("action", ""))),
                payload=doc.get("payload") or {},
            )
        except ValueError:
            return None


def parse_button_id(button_id: str) -> tuple[str, str] | None:
    """Zerlegt eine Button-ID `{verb}_{action_id}` deterministisch.

    Verben: confirm / cancel. Gibt (verb, action_id) zurück.
    """
    for verb in ("confirm", "cancel"):
        prefix = f"{verb}_"
        if button_id.startswith(prefix) and len(button_id) > len(prefix):
            return verb, button_id[len(prefix) :]
    return None
