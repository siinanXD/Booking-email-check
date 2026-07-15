"""Telefonnummer-Normalisierung (nur Ziffern) für Nummern-Vergleiche.

Wird sowohl beim WhatsApp-Absender-Matching (Features) als auch in den
Repositories (Infrastructure) genutzt – deshalb liegt es in ``core``.
"""

from __future__ import annotations


def normalize_phone_digits(phone: str | None) -> str:
    """Reduziert eine Telefonnummer auf reine Ziffern (Meta-wa_id-Format).

    Beispiel: ``"+49 157 1234567"`` -> ``"491571234567"``. ``None``/leer -> ``""``.
    """
    return "".join(ch for ch in (phone or "") if ch.isdigit())
