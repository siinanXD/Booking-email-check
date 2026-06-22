"""Tests für filter_messages_for_initial_sync."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.core.models.email import IncomingEmail
from backend.features.mail.ingest_window import (
    filter_messages_for_initial_sync,
    filter_messages_since_cutoff,
)


def _mail(msg_id: str, received_at: datetime) -> IncomingEmail:
    return IncomingEmail(
        message_id=msg_id,
        from_address="guest@example.com",
        received_at=received_at,
    )


def test_initial_sync_50_before_plus_all_after() -> None:
    anchor = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    messages: list[IncomingEmail] = []
    for i in range(100):
        messages.append(
            _mail(
                f"before-{i}",
                anchor - timedelta(hours=i + 1),
            )
        )
    for i in range(10):
        messages.append(
            _mail(
                f"after-{i}",
                anchor + timedelta(hours=i),
            )
        )

    selected = filter_messages_for_initial_sync(messages, anchor, 50)
    after_ids = {m.message_id for m in selected if m.received_at >= anchor}
    before_ids = {m.message_id for m in selected if m.received_at < anchor}

    assert len(after_ids) == 10
    assert len(before_ids) == 50
    assert all(mid.startswith("after-") for mid in after_ids)
    assert all(mid.startswith("before-") for mid in before_ids)
    assert "before-0" in before_ids
    assert "before-49" in before_ids
    assert "before-50" not in before_ids


def test_initial_sync_fewer_than_lookback_before() -> None:
    anchor = datetime(2026, 6, 1, tzinfo=UTC)
    messages = [
        _mail("b1", anchor - timedelta(days=1)),
        _mail("b2", anchor - timedelta(days=2)),
        _mail("a1", anchor),
    ]
    selected = filter_messages_for_initial_sync(messages, anchor, 50)
    assert len(selected) == 3


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
