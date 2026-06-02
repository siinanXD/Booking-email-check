"""Tests für Ingestion."""

from __future__ import annotations

from models.email import ProcessingState
from routers.ingestion import IngestionRouter
from schemas.booking.triage import TriageOutcome
from utils.text import strip_quoted_history


def test_strip_quoted_history() -> None:
    body = "Neue Anfrage\n\nOn Mon, Jun 1 wrote:\n> old"
    assert "Neue Anfrage" in strip_quoted_history(body)
    assert "old" not in strip_quoted_history(body)


def test_ingest_persists_booking_email(
    ingestion_service,
    email_repo,
    booking_emails,
) -> None:
    payload = booking_emails[0]
    router = IngestionRouter(ingestion_service)
    result = router.ingest_email(payload)
    assert result.duplicate is False
    assert result.email.message_id == payload.message_id
    stored = email_repo.get_by_message_id(payload.message_id)
    assert stored is not None
    assert stored.triage_outcome == TriageOutcome.RELEVANT.value


def test_ingest_dedup(
    ingestion_service,
    booking_emails,
) -> None:
    payload = booking_emails[0]
    router = IngestionRouter(ingestion_service)
    first = router.ingest_email(payload)
    second = router.ingest_email(payload)
    assert first.duplicate is False
    assert second.duplicate is True


def test_ingest_normalizes_html_body(
    ingestion_service,
    booking_emails,
) -> None:
    payload = booking_emails[4]
    router = IngestionRouter(ingestion_service)
    result = router.ingest_email(payload)
    assert "HTML" in result.email.body_text or "Inhalt" in result.email.body_text


def test_ingest_discards_phishing(
    ingestion_service,
    booking_emails,
) -> None:
    payload = booking_emails[1]
    router = IngestionRouter(ingestion_service)
    result = router.ingest_email(payload)
    assert result.discarded is True
    assert result.email.processing_state == ProcessingState.DISCARDED
