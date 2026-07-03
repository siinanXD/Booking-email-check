"""Domänenmodelle des Putzplan-Features."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(UTC)


class CleaningTaskStatus(StrEnum):
    """Lebenszyklus eines Putzauftrags."""

    # Buchung erkannt, aber (noch) kein Putzpartner für die Wohnung hinterlegt.
    UNASSIGNED = "unassigned"
    # Putzpartner zugeordnet, Auftrag steht.
    SCHEDULED = "scheduled"
    # WhatsApp an den Putzpartner wurde versendet.
    NOTIFIED = "notified"
    # Vom Gastgeber/Partner als erledigt markiert.
    DONE = "done"
    # Buchung storniert – Auftrag entfällt.
    CANCELLED = "cancelled"


# Quellen für Statusübergänge (Audit).
SOURCE_BOOKING_EMAIL = "booking_email"
SOURCE_CANCELLATION_EMAIL = "cancellation_email"
SOURCE_MANUAL = "manual"
SOURCE_BACKFILL = "backfill"
SOURCE_SYSTEM = "system"


class CleaningStatusEvent(BaseModel):
    """Ein Statusübergang im Verlauf eines Putzauftrags."""

    status: CleaningTaskStatus
    at: datetime = Field(default_factory=_now)
    source: str = SOURCE_SYSTEM
    note: str | None = None


class CleaningPartner(BaseModel):
    """Putzpartner mit Kontaktdaten, zugeordnet zu Wohnungen."""

    partner_id: str
    account_id: str | None = None
    name: str
    address: str | None = None
    contact_person: str | None = None
    phone: str | None = None  # E.164
    locale: str = "de"
    property_names: list[str] = Field(default_factory=list)
    active: bool = True
    # Testmodus: Partner erhält KEINE echte WhatsApp (für gefahrlose Selbsttests).
    test_mode: bool = False
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    def to_mongo(self) -> dict[str, Any]:
        """Serialisiert für MongoDB (inkl. normalisierter Suchspalte)."""
        doc = self.model_dump(mode="json")
        doc["property_names_lower"] = [
            name.strip().lower()
            for name in self.property_names
            if name and name.strip()
        ]
        return doc

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> CleaningPartner:
        """Deserialisiert aus einem MongoDB-Dokument."""
        payload = {k: v for k, v in doc.items() if k != "_id"}
        if "_id" in doc:
            payload["partner_id"] = str(doc["_id"])
        return cls.model_validate(payload)


class CleaningTask(BaseModel):
    """Ein Putzauftrag, abgeleitet aus einer Buchung."""

    task_id: str
    account_id: str | None = None
    booking_number: str | None = None
    correlation_id: str | None = None
    property_name: str | None = None
    room_number: str | None = None
    guest_name: str | None = None
    check_in: date | None = None
    check_out: date | None = None
    cleaning_date: date | None = None
    partner_id: str | None = None
    status: CleaningTaskStatus = CleaningTaskStatus.UNASSIGNED
    source_intent: str | None = None
    # Freies Bemerkungsfeld (z. B. frühe Anreise, Sonderwünsche) – manuell gepflegt.
    note: str | None = None
    # Schutz vor automatischem Überschreiben nach manueller Bearbeitung.
    manually_edited: bool = False
    status_history: list[CleaningStatusEvent] = Field(default_factory=list)
    # Spiegelt das Ergebnis des letzten WhatsApp-Versands (Outbox).
    last_notification_status: str | None = None
    last_notification_error: str | None = None
    notified_at: datetime | None = None
    done_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    def record_status(
        self,
        status: CleaningTaskStatus,
        *,
        source: str = SOURCE_SYSTEM,
        note: str | None = None,
    ) -> None:
        """Setzt den Status und ergänzt den Audit-Verlauf."""
        self.status = status
        self.status_history.append(
            CleaningStatusEvent(status=status, source=source, note=note)
        )
        self.updated_at = _now()
        if status == CleaningTaskStatus.NOTIFIED and self.notified_at is None:
            self.notified_at = _now()
        elif status == CleaningTaskStatus.DONE:
            self.done_at = _now()
        elif status == CleaningTaskStatus.CANCELLED:
            self.cancelled_at = _now()

    def to_mongo(self) -> dict[str, Any]:
        """Serialisiert für MongoDB."""
        return self.model_dump(mode="json")

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> CleaningTask:
        """Deserialisiert aus einem MongoDB-Dokument."""
        payload = {k: v for k, v in doc.items() if k != "_id"}
        if "_id" in doc:
            payload["task_id"] = str(doc["_id"])
        return cls.model_validate(payload)
