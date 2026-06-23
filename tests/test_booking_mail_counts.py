"""Tests für Buchungs-Mail-Zählungen."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from backend.ai.domain.booking.booking_mail_counts import (
    aggregate_booking_mail_stats,
    count_booking_mails,
    latest_booking_received_at,
)
from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.models.email import ProcessingState, StoredEmail
from backend.infrastructure.repositories.email_repository import EmailRepository
from backend.infrastructure.repositories.extraction_repository import (
    ExtractionRepository,
)


class _FakeExtractionRepo(ExtractionRepository):
    """Test-Double ohne MongoDB."""

    def __init__(self, mapping: dict[str, BookingExtraction]) -> None:
        self._mapping = mapping
        self.call_count = 0

    def map_by_correlation_ids(
        self,
        correlation_ids: list[str],
        *,
        account_id: str | None = None,
    ) -> dict[str, BookingExtraction]:
        self.call_count += 1
        return self._mapping


def _stored(
    *,
    message_id: str,
    correlation_id: str,
    received_at: datetime,
    subject: str = "Buchung Ferienwohnung",
) -> dict[str, object]:
    email = StoredEmail(
        message_id=message_id,
        from_address="guest@example.com",
        subject=subject,
        body_text="Ich möchte buchen",
        received_at=received_at,
        correlation_id=correlation_id,
        processing_state=ProcessingState.RECEIVED,
        updated_at=received_at,
        account_id="acc-1",
    )
    return email.to_mongo()


def _email_repo(docs: list[dict[str, object]]) -> EmailRepository:
    repo = EmailRepository.__new__(EmailRepository)
    repo._col = MagicMock()
    repo._col.aggregate.return_value = docs
    return repo


def test_aggregate_booking_mail_stats_single_batch_and_pass() -> None:
    """Ein Scan + ein Batch-Load liefern alle KPIs."""
    today = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)
    week_day = datetime(2026, 6, 2, 10, 0, tzinfo=UTC)

    email_repo = _email_repo(
        [
            _stored(message_id="m1", correlation_id="c1", received_at=today),
            _stored(message_id="m2", correlation_id="c2", received_at=week_day),
        ]
    )
    extraction_repo = _FakeExtractionRepo(
        {
            "c1": BookingExtraction(
                intent=BookingIntent.NEW_BOOKING,
                booking_number="B1",
            ),
            "c2": BookingExtraction(
                intent=BookingIntent.CHANGE,
                booking_number="B2",
            ),
        }
    )

    stats = aggregate_booking_mail_stats(
        email_repo,
        extraction_repo,
        account_id="acc-1",
        today_iso="2026-06-05T00:00:00+00:00",
        week_iso="2026-06-01T00:00:00+00:00",
    )

    assert extraction_repo.call_count == 1
    assert stats.booking_total == 2
    assert stats.booking_week == 2
    assert stats.intents_today[BookingIntent.NEW_BOOKING.value] == 1
    assert stats.intents_all[BookingIntent.CHANGE.value] == 1
    assert stats.latest_booking_received_at == today


def test_intents_window_excludes_mails_before_window() -> None:
    """intents_window zählt nur Mails ab window_iso; intents_all zählt alle."""
    recent = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)
    old = datetime(2026, 4, 1, 10, 0, tzinfo=UTC)  # vor dem 30-Tage-Fenster
    email_repo = _email_repo(
        [
            _stored(message_id="m1", correlation_id="c1", received_at=recent),
            _stored(message_id="m2", correlation_id="c2", received_at=old),
        ]
    )
    extraction_repo = _FakeExtractionRepo(
        {
            "c1": BookingExtraction(intent=BookingIntent.NEW_BOOKING),
            "c2": BookingExtraction(intent=BookingIntent.NEW_BOOKING),
        }
    )

    stats = aggregate_booking_mail_stats(
        email_repo,
        extraction_repo,
        account_id="acc-1",
        today_iso="2026-06-05T00:00:00+00:00",
        week_iso="2026-06-01T00:00:00+00:00",
        window_iso="2026-05-06T00:00:00+00:00",
    )

    nb = BookingIntent.NEW_BOOKING.value
    assert stats.intents_all[nb] == 2
    assert stats.intents_window[nb] == 1


def test_count_booking_mails_uses_batch_load() -> None:
    """count_booking_mails lädt Extraktionen gebündelt."""
    received = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)
    email_repo = _email_repo(
        [_stored(message_id="m1", correlation_id="c1", received_at=received)]
    )
    extraction_repo = _FakeExtractionRepo(
        {
            "c1": BookingExtraction(
                intent=BookingIntent.NEW_BOOKING,
                booking_number="B1",
            ),
        }
    )

    total, booking, by_intent = count_booking_mails(
        email_repo,
        extraction_repo,
        account_id="acc-1",
    )

    assert extraction_repo.call_count == 1
    assert total == 1
    assert booking == 1
    assert by_intent[BookingIntent.NEW_BOOKING.value] == 1


def test_latest_booking_received_at_delegates_to_aggregate() -> None:
    """latest_booking_received_at nutzt aggregierte Stats."""
    received = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)
    email_repo = _email_repo(
        [_stored(message_id="m1", correlation_id="c1", received_at=received)]
    )
    extraction_repo = _FakeExtractionRepo(
        {
            "c1": BookingExtraction(
                intent=BookingIntent.NEW_BOOKING,
                booking_number="B1",
            ),
        }
    )

    latest = latest_booking_received_at(
        email_repo,
        extraction_repo,
        account_id="acc-1",
    )

    assert latest == received
    assert extraction_repo.call_count == 1
