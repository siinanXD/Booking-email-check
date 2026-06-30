"""Deterministische Identität & Termin-Logik für Putzaufträge."""

from __future__ import annotations

import hashlib
from datetime import date, timedelta


def cleaning_task_id(
    *,
    account_id: str | None,
    booking_number: str | None,
    property_name: str | None,
    check_out: date | None,
    guest_name: str | None,
) -> str:
    """Stabile task_id, damit Re-Ingestion denselben Auftrag upsertet.

    Bevorzugt die Buchungsnummer; fällt sonst auf Wohnung + Check-out + Gast
    zurück, sodass mehrfach eintreffende Buchungsmails nicht duplizieren.
    """
    acc = (account_id or "").strip().lower()
    if booking_number and booking_number.strip():
        seed = f"{acc}:bn:{booking_number.strip().lower()}"
    else:
        prop = (property_name or "").strip().lower()
        out = check_out.isoformat() if check_out else ""
        guest = (guest_name or "").strip().lower()
        seed = f"{acc}:fb:{prop}:{out}:{guest}"
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()  # noqa: S324


def cleaning_date_for(check_out: date | None, offset_days: int) -> date | None:
    """Putztermin = Check-out + konfigurierbarer Offset (0 = Abreisetag)."""
    if check_out is None:
        return None
    return check_out + timedelta(days=max(0, offset_days))
