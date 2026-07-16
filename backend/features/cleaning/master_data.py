"""Stammdaten eines Putzauftrags aus der Mail nachziehen."""

from __future__ import annotations

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.features.cleaning.models import CleaningTask


def refresh_master_data(task: CleaningTask, extraction: BookingExtraction) -> None:
    """Zieht Zimmer, Objekt und Gast aus der Mail nach.

    Ohne das blieb ein einmal falsch angelegter Auftrag für immer falsch: Folge-
    mails (Änderung, Storno, Re-Ingestion) aktualisierten nur Termine, Status und
    Partner. Im Bestand standen dadurch acht Aufträge mit room_number=None,
    obwohl "Zimmer Nr. 3" wörtlich in der Mail stand und der Parser es korrekt
    las — der Zimmer-Fix vom 3. Juli erreichte die Altdaten schlicht nie.

    Bewusst unabhängig von ``manually_edited``: das Flag schützt Status, Partner
    und Bemerkung — die Stammdaten sind über die API gar nicht editierbar und
    dürfen deshalb immer der Mail folgen. Leere Extraktionsfelder überschreiben
    nichts, sonst würde eine dürftige Folgemail gute Daten löschen.
    """
    if extraction.room_number:
        task.room_number = extraction.room_number
    if extraction.property_name:
        task.property_name = extraction.property_name
    if extraction.guest_name:
        task.guest_name = extraction.guest_name
    if extraction.booking_number:
        task.booking_number = extraction.booking_number
