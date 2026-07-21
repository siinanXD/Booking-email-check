"""Deterministische Identität & Termin-Logik für Putzaufträge."""

from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.ai.domain.booking.extraction import BookingExtraction


def cleaning_task_id(
    *,
    account_id: str | None,
    booking_number: str | None,
    property_name: str | None,
    check_out: date | None,
    guest_name: str | None,
    room_number: str | None = None,
) -> str:
    """Stabile task_id, damit Re-Ingestion denselben Auftrag upsertet.

    Bevorzugt die Buchungsnummer; fällt sonst auf Wohnung + Check-out + Gast
    zurück, sodass mehrfach eintreffende Buchungsmails nicht duplizieren.

    Das Zimmer gehört in beide Zweige: eine Reservierung über zwei Zimmer
    trägt *eine* Buchungsnummer, und ohne das Zimmer im Seed überschrieb der
    zweite Auftrag den ersten — geputzt wurde dann nur eines der Zimmer.
    """
    acc = (account_id or "").strip().lower()
    room = (room_number or "").strip().lower()
    if booking_number and booking_number.strip():
        seed = f"{acc}:bn:{booking_number.strip().lower()}"
    else:
        prop = (property_name or "").strip().lower()
        out = check_out.isoformat() if check_out else ""
        guest = (guest_name or "").strip().lower()
        seed = f"{acc}:fb:{prop}:{out}:{guest}"
    # Ohne Zimmerangabe bleibt der Seed unverändert — Bestandsaufträge aus
    # Einzelzimmer-Buchungen behalten dadurch ihre bisherige task_id.
    if room:
        seed = f"{seed}:room:{room}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()  # noqa: S324


def task_id_for(extraction: BookingExtraction, account_id: str) -> str:
    """task_id einer Buchung — inklusive Zimmer."""
    return cleaning_task_id(
        account_id=account_id,
        booking_number=extraction.booking_number,
        property_name=extraction.property_name,
        check_out=extraction.check_out,
        guest_name=extraction.guest_name,
        room_number=extraction.room_number,
    )


def cleaning_partner_id(account_id: str, phone: str) -> str:
    """Stabile partner_id aus der Telefonnummer — eine Nummer, eine Person.

    Bot und Weboberfläche legen denselben Mitarbeiter sonst unter zwei IDs an;
    im Bestand stand dieselbe Putzkraft dadurch doppelt, je einmal pro Objekt.
    """
    seed = f"{(account_id or '').strip().lower()}:{phone.strip()}"
    return "cp_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def cleaning_date_for(check_out: date | None, offset_days: int) -> date | None:
    """Putztermin = Check-out + konfigurierbarer Offset (0 = Abreisetag)."""
    if check_out is None:
        return None
    return check_out + timedelta(days=max(0, offset_days))
