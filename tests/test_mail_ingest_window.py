"""Tests für filter_messages_since_cutoff (zeitbasierter Erst-Sync)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.core.models.email import IncomingEmail
from backend.features.mail.ingest_window import filter_messages_since_cutoff


def _mail(msg_id: str, received_at: datetime) -> IncomingEmail:
    return IncomingEmail(
        message_id=msg_id,
        from_address="guest@example.com",
        received_at=received_at,
    )


def test_filter_messages_since_cutoff_one_day() -> None:
    """Zeitbasierter Cutoff: nur Mails ab anchor - 1 Tag."""
    anchor = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
    messages = [
        _mail("after", anchor + timedelta(hours=1)),
        _mail("within", anchor - timedelta(hours=10)),
        _mail("edge", anchor - timedelta(days=1)),
        _mail("too-old", anchor - timedelta(days=1, hours=1)),
    ]
    selected = {m.message_id for m in filter_messages_since_cutoff(messages, anchor, 1)}
    assert selected == {"after", "within", "edge"}


def test_filter_messages_since_cutoff_drops_missing_received_at() -> None:
    anchor = datetime(2026, 6, 10, tzinfo=UTC)
    msg = _mail("ok", anchor)
    no_date = IncomingEmail(
        message_id="no-date",
        from_address="g@example.com",
        received_at=anchor,
    )
    no_date.received_at = None  # type: ignore[assignment]
    selected = filter_messages_since_cutoff([msg, no_date], anchor, 1)
    assert [m.message_id for m in selected] == ["ok"]
