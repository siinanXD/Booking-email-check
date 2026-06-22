"""Zeitfenster für zuverlässigen Graph-Poll (neueste Mails zuerst)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def parse_iso_datetime(value: str) -> datetime:
    """Parst ISO-8601 (Mongo/Graph) nach UTC."""
    text = value.replace("Z", "+00:00")
    return datetime.fromisoformat(text).astimezone(UTC)


def format_graph_datetime(dt: datetime) -> str:
    """Graph-OData UTC ohne Subsekunden."""
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_poll_since(
    *,
    max_received_at: str | None,
    last_sync_at: datetime | None,
    overlap: timedelta = timedelta(hours=24),
    default_window: timedelta = timedelta(days=7),
) -> datetime:
    """Untergrenze für ``receivedDateTime ge …`` (Graph sortiert dann zuverlässig).

    Ohne ``$filter`` auf ``receivedDateTime`` ignoriert Microsoft Graph oft
    ``$orderby`` — dann liefert ``$top=100`` beliebige alte Mails statt der
    neuesten (Symptom: ``duplicates=100``, neue Test-Mails fehlen).
    """
    now = datetime.now(UTC)
    candidates: list[datetime] = [now - default_window]
    if max_received_at:
        try:
            newest = parse_iso_datetime(max_received_at)
            candidates.append(newest - overlap)
        except ValueError:
            pass
    if last_sync_at is not None:
        synced = (
            last_sync_at.replace(tzinfo=UTC)
            if last_sync_at.tzinfo is None
            else last_sync_at.astimezone(UTC)
        )
        candidates.append(synced - overlap)
    return max(candidates)


def format_imap_since_date(dt: datetime) -> str:
    """IMAP ``SEARCH SINCE`` (engl. Monatskürzel, nur Datum)."""
    return dt.astimezone(UTC).strftime("%d-%b-%Y")


def resolve_poll_since_for_account(
    *,
    max_received_at: str | None,
    last_sync_at: datetime | None,
    initial_sync: bool = False,
    ingest_anchor_at: datetime | None = None,
    lookback_days: int = 1,
) -> datetime:
    """Poll-Untergrenze inkl. Erst-Sync-Fenster (Graph + IMAP).

    Beim Erst-Sync wird die Rückschau auf ``lookback_days`` ab dem Anker
    (Anmeldezeitpunkt) **begrenzt** — ältere Mails werden nicht importiert.
    """
    since = compute_poll_since(
        max_received_at=max_received_at,
        last_sync_at=last_sync_at,
    )
    if initial_sync and ingest_anchor_at is not None:
        anchor_utc = (
            ingest_anchor_at.astimezone(UTC)
            if ingest_anchor_at.tzinfo is not None
            else ingest_anchor_at.replace(tzinfo=UTC)
        )
        since = max(since, anchor_utc - timedelta(days=lookback_days))
    return since
