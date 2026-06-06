"""Tests für Graph-Poll-Zeitfenster."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.infrastructure.adapters.outlook.poll_window import (
    compute_poll_since,
    format_graph_datetime,
    parse_iso_datetime,
)


def test_format_graph_datetime_utc() -> None:
    dt = datetime(2026, 6, 6, 13, 44, 0, tzinfo=UTC)
    assert format_graph_datetime(dt) == "2026-06-06T13:44:00Z"


def test_compute_poll_since_uses_max_received_overlap() -> None:
    newest = datetime(2026, 6, 6, 12, 0, tzinfo=UTC)
    since = compute_poll_since(
        max_received_at=newest.isoformat().replace("+00:00", "Z"),
        last_sync_at=None,
        overlap=timedelta(hours=24),
        default_window=timedelta(days=7),
    )
    assert since == newest - timedelta(hours=24)


def test_compute_poll_since_default_window_when_empty() -> None:
    now = datetime.now(UTC)
    since = compute_poll_since(max_received_at=None, last_sync_at=None)
    assert since <= now
    assert since >= now - timedelta(days=7, minutes=1)


def test_parse_iso_datetime_z_suffix() -> None:
    assert parse_iso_datetime("2026-06-06T13:44:00Z") == datetime(
        2026, 6, 6, 13, 44, tzinfo=UTC
    )
