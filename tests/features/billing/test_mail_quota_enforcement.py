"""Mail-Poll und Ingestion bei erschöpfter Quota."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from backend.ai.services.ingestion import IngestResult
from backend.core.models.email import IncomingEmail, ProcessingState, StoredEmail
from backend.features.billing.entitlement_service import QuotaStatus
from backend.features.mail.mail_poll_service import MailPollService
from backend.infrastructure.adapters.mail.ingestion import (
    MailIngestionRunner,
    MailPollRunResult,
)


def test_poll_skips_quota_exhausted_account() -> None:
    mail_repo = MagicMock()
    mail_repo.list_pollable.return_value = [
        MagicMock(account_id="a1", provider="outlook"),
        MagicMock(account_id="a2", provider="outlook"),
    ]
    account_repo = MagicMock()
    active = MagicMock(id="a1", expires_at=None)
    exhausted = MagicMock(id="a2", expires_at=None)
    account_repo.list_by_status.return_value = [active, exhausted]

    runner = MagicMock()
    runner.run_for_account.return_value = MailPollRunResult(processed=1, items=[])

    entitlement = MagicMock()
    entitlement.mail_quota.side_effect = lambda aid: QuotaStatus(
        used=100,
        limit=50,
        exhausted=(aid == "a2"),
    )

    svc = MailPollService(
        mail_repo, account_repo, runner, entitlement_service=entitlement
    )
    result = svc.run_all()
    assert result.accounts_polled == 1
    runner.run_for_account.assert_called_once_with("a1")


def test_ingestion_stores_quota_exceeded_without_metrics() -> None:
    payload = IncomingEmail(
        message_id="msg-1",
        from_address="guest@example.com",
        subject="Booking",
        body_text="hello",
        received_at=datetime.now(UTC),
        account_id="acc-1",
        correlation_id="corr-1",
    )
    entitlement = MagicMock()
    entitlement.mail_quota.return_value = QuotaStatus(used=10, limit=10, exhausted=True)

    router = MagicMock()
    stored = StoredEmail(
        **payload.model_dump(), processing_state=ProcessingState.RECEIVED
    )
    router.ingest_email.return_value = IngestResult(
        email=stored, duplicate=False, discarded=False
    )
    email_repo = MagicMock()

    runner = MailIngestionRunner(
        MagicMock(),
        MagicMock(),
        email_repo,
        MagicMock(),
        MagicMock(),
        ingestion_router=router,
        entitlement_service=entitlement,
    )
    assert runner._quota_blocks_processing("acc-1")
    runner._store_quota_exceeded(payload, "acc-1")
    router.ingest_email.assert_called_once()
    email_repo.update_processing_state.assert_called_once()
    assert (
        email_repo.update_processing_state.call_args[0][1]
        == ProcessingState.QUOTA_EXCEEDED
    )
