"""Polling-Heartbeat: Staleness-Logik und Repo-Heartbeat."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.api.app import _poll_stale
from backend.infrastructure.repositories.mail_connection_repository import (
    MailConnectionRecord,
    MailConnectionRepository,
)


def test_poll_stale_logic() -> None:
    now = datetime(2026, 6, 23, 12, 0, tzinfo=UTC)
    fresh = now - timedelta(seconds=60)
    old = now - timedelta(seconds=2000)
    assert _poll_stale(fresh, expected=True, now=now, threshold_seconds=900) is False
    assert _poll_stale(old, expected=True, now=now, threshold_seconds=900) is True
    assert _poll_stale(None, expected=True, now=now, threshold_seconds=900) is True
    # Keine pollbaren Accounts → nie stale (kein Fehlalarm bei frischem Deploy).
    assert _poll_stale(None, expected=False, now=now, threshold_seconds=900) is False


def test_newest_sync_at_returns_max(mock_db) -> None:
    repo = MailConnectionRepository(mock_db)
    repo.save(
        MailConnectionRecord(
            account_id="a", last_sync_at=datetime(2026, 6, 1, tzinfo=UTC)
        )
    )
    repo.save(
        MailConnectionRecord(
            account_id="b", last_sync_at=datetime(2026, 6, 5, tzinfo=UTC)
        )
    )
    assert repo.newest_sync_at() == datetime(2026, 6, 5, tzinfo=UTC)


def test_newest_sync_at_none_when_empty(mock_db) -> None:
    assert MailConnectionRepository(mock_db).newest_sync_at() is None
