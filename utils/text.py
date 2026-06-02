"""Text-Hilfsfunktionen für Mail-Verarbeitung."""

from __future__ import annotations

import re

_QUOTE_PATTERNS = [
    re.compile(r"^On .+ wrote:\s*$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^Am .+ schrieb.*:\s*$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^-{2,}\s*Original Message\s*-{2,}", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^>{1,}\s?", re.MULTILINE),
]


def strip_quoted_history(body: str) -> str:
    """Entfernt typische Zitat-Blöcke aus dem Mail-Body (heuristisch)."""
    if not body.strip():
        return body
    cut_at: int | None = None
    for pattern in _QUOTE_PATTERNS:
        match = pattern.search(body)
        if match and (cut_at is None or match.start() < cut_at):
            cut_at = match.start()
    if cut_at is not None and cut_at > 0:
        return body[:cut_at].strip()
    return body.strip()


def normalize_body(body_text: str, body_html: str | None = None) -> str:
    """Bevorzugt Plaintext; HTML nur als Fallback (Tags entfernt)."""
    if body_text.strip():
        return strip_quoted_history(body_text)
    if not body_html:
        return ""
    text = re.sub(r"<[^>]+>", " ", body_html)
    text = re.sub(r"\s+", " ", text).strip()
    return strip_quoted_history(text)
