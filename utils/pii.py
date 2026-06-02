"""PII-Maskierung vor Logging/Tracing."""

from __future__ import annotations

import re

_EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_PHONE = re.compile(r"\+?\d[\d\s\-()]{7,}\d")


def mask_pii(text: str) -> str:
    """Ersetzt E-Mail-Adressen und Telefonnummern durch Platzhalter."""
    masked = _EMAIL.sub("[EMAIL]", text)
    return _PHONE.sub("[PHONE]", masked)
