"""Begrenzter Erst-Import: Anker + Lookback."""

from __future__ import annotations

import logging

from backend.core.models.email import IncomingEmail

logger = logging.getLogger(__name__)


def filter_messages_for_initial_sync(
    messages: list[IncomingEmail],
    anchor: object,
    lookback: int,
) -> list[IncomingEmail]:
    """Filtert Mails für den ersten Sync (neueste zuerst erwartet).

    - Alle Mails mit received_at >= anchor
    - Plus die neuesten `lookback` Mails vor dem Anker
    - Mails ohne received_at werden verworfen
    """
    from datetime import datetime

    if not isinstance(anchor, datetime):
        raise TypeError("anchor must be datetime")

    valid: list[IncomingEmail] = []
    for msg in messages:
        if msg.received_at is None:
            logger.warning("Skipping message without received_at: %s", msg.message_id)
            continue
        valid.append(msg)

    sorted_msgs = sorted(valid, key=lambda m: m.received_at, reverse=True)
    after = [m for m in sorted_msgs if m.received_at >= anchor]
    before = [m for m in sorted_msgs if m.received_at < anchor]
    return after + before[:lookback]
