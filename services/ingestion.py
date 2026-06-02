"""Ingestion-Service: Normalisierung, Dedup, Persistenz."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from models.email import IncomingEmail, ProcessingState, StoredEmail
from repositories.email_repository import EmailRepository
from schemas.booking.triage import TriageOutcome
from services.triage import TriageService
from utils.text import normalize_body


@dataclass
class IngestResult:
    """Ergebnis einer Ingestion."""

    email: StoredEmail
    duplicate: bool
    discarded: bool
    triage_reason: str = ""


class IngestionService:
    """Verarbeitet eingehende Mails bis nach Triage."""

    def __init__(
        self,
        email_repo: EmailRepository,
        triage_service: TriageService | None = None,
    ) -> None:
        self._email_repo = email_repo
        self._triage = triage_service or TriageService()

    def ingest(self, payload: IncomingEmail) -> IngestResult:
        """Normalisiert, dedupliziert, triagiert und speichert."""
        existing = self._email_repo.get_by_message_id(payload.message_id)
        if existing is not None:
            return IngestResult(email=existing, duplicate=True, discarded=False)

        normalized = self._normalize(payload)
        triage = self._triage.triage(normalized)
        now = datetime.now(UTC)

        state = ProcessingState.RECEIVED
        discarded = False
        if triage.outcome == TriageOutcome.SPAM_PHISHING:
            state = ProcessingState.DISCARDED
            discarded = True
        elif triage.outcome == TriageOutcome.RELEVANT:
            state = ProcessingState.TRIAGED

        stored = StoredEmail(
            **normalized.model_dump(),
            triage_outcome=triage.outcome.value,
            processing_state=state,
            created_at=now,
            updated_at=now,
        )
        saved = self._email_repo.upsert_by_message_id(stored)
        return IngestResult(
            email=saved,
            duplicate=False,
            discarded=discarded,
            triage_reason=triage.reason,
        )

    def _normalize(self, payload: IncomingEmail) -> IncomingEmail:
        """Body bereinigen; übrige Felder unverändert."""
        body = normalize_body(payload.body_text, payload.body_html)
        return payload.model_copy(update={"body_text": body})
