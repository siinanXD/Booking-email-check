"""Reine Heartbeat-Logik fürs Status-Board (kein Import aus app.py)."""

from __future__ import annotations

from datetime import datetime


def poll_stale(
    newest: datetime | None,
    *,
    expected: bool,
    now: datetime,
    threshold_seconds: int,
) -> bool:
    """True, wenn Polling erwartet wird, aber zu lange kein Zyklus durchlief."""
    if not expected:
        return False
    if newest is None:
        return True
    return (now - newest).total_seconds() > threshold_seconds
