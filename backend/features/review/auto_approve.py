"""Entscheidungslogik für die Auto-Freigabe ab Konfidenz.

Die eigentliche Antwort-Pipeline ruft :func:`should_auto_approve` auf, bevor ein
Entwurf in die Review-Warteschlange gelegt wird. Liegt die Konfidenz über der
Mandanten-Schwelle **und** ist der Intent für die Auto-Freigabe aktiviert, darf
der Entwurf automatisch versendet (statt nur entworfen) werden. Jeder
Auto-Versand wird protokolliert (Audit + Undo-Fenster) — siehe Aufrufer.
"""

from __future__ import annotations

from backend.infrastructure.repositories.platform_settings_repository import (
    AutoApproveSettings,
)

# Pipeline-Intent (effective_intent) → Auto-Freigabe-Schlüssel.
_INTENT_KEYS: dict[str, str] = {
    "new_booking": "booking",
    "booking": "booking",
    "cancellation": "cancellation",
    "change": "change",
    "modification": "change",
    "guest_inquiry": "inquiry",
    "inquiry": "inquiry",
}


def normalize_confidence(confidence: float | int | None) -> float:
    """Bringt Konfidenz auf Prozent (0–100).

    Werte ≤ 1 werden als Bruch interpretiert (0.96 → 96), größere Werte gelten
    bereits als Prozent.
    """
    if confidence is None:
        return 0.0
    value = float(confidence)
    if value <= 1.0:
        value *= 100.0
    return max(0.0, min(100.0, value))


def auto_approve_key(intent: str | None) -> str | None:
    """Mappt einen Pipeline-Intent auf den Auto-Freigabe-Schlüssel."""
    if not intent:
        return None
    return _INTENT_KEYS.get(intent.strip().lower())


def should_auto_approve(
    confidence: float | int | None,
    intent: str | None,
    settings: AutoApproveSettings,
) -> bool:
    """True, wenn der Entwurf automatisch freigegeben werden darf."""
    if not settings.enabled:
        return False
    key = auto_approve_key(intent)
    if key is None or not settings.per_intent.get(key, False):
        return False
    return normalize_confidence(confidence) >= settings.threshold
