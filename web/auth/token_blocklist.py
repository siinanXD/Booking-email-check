"""In-Memory JWT-Blocklist (MVP)."""

from __future__ import annotations

_revoked: set[str] = set()


def revoke(jti: str) -> None:
    """Token widerrufen."""
    _revoked.add(jti)


def is_revoked(jti: str) -> bool:
    """Prüft ob Token widerrufen wurde."""
    return jti in _revoked


def clear_for_tests() -> None:
    """Leert Blocklist (nur Tests)."""
    _revoked.clear()
