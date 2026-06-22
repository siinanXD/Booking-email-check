"""Tests für Graph-Poll-Zeitfenster."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.infrastructure.adapters.outlook.poll_window import (
    compute_poll_since,
    format_graph_datetime,
    format_imap_since_date,
    parse_iso_datetime,
    resolve_poll_since_for_account,
)


def test_format_graph_datetime_utc() -> None:
    dt = datetime(2026, 6, 6, 13, 44, 0, tzinfo=UTC)
    assert format_graph_datetime(dt) == "2026-06-06T13:44:00Z"


def test_compute_poll_since_uses_max_received_overlap() -> None:
    # Relativ zu jetzt, damit ``newest - overlap`` immer das Maximum gegenüber
    # ``now - default_window`` bleibt (sonst gewinnt mit fortschreitender Zeit
    # das Default-Fenster und der Test rottet).
    newest = datetime.now(UTC) - timedelta(hours=1)
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


def test_format_imap_since_date() -> None:
    dt = datetime(2026, 6, 6, 13, 44, 0, tzinfo=UTC)
    assert format_imap_since_date(dt) == "06-Jun-2026"


def test_resolve_poll_since_for_account_initial_sync() -> None:
    anchor = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
    since = resolve_poll_since_for_account(
        max_received_at=None,
        last_sync_at=None,
        initial_sync=True,
        ingest_anchor_at=anchor,
    )
    assert since == anchor - timedelta(days=60)
