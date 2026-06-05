"""Orchestriert automatisches Mail-Polling über alle Mandanten."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from backend.core.config.settings import Settings
from backend.infrastructure.adapters.mail.ingestion import MailIngestionRunner
from backend.infrastructure.repositories.account_repository import AccountRepository
from backend.infrastructure.repositories.mail_connection_repository import (
    MailConnectionRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class AccountPollSummary:
    """Ergebnis eines Poll-Laufs für einen Mandanten."""

    account_id: str
    provider: str
    processed: int
    duplicates: int
    item_errors: list[str] = field(default_factory=list)
    fetch_error: str | None = None

    @property
    def success(self) -> bool:
        return self.fetch_error is None and not self.item_errors


@dataclass
class MailPollBatchResult:
    """Gesamtergebnis eines Poll-Laufs."""

    accounts_polled: int
    total_processed: int
    summaries: list[AccountPollSummary]


class MailPollService:
    """Pollt Postfächer aller aktiven Mandanten mit gültiger Konfiguration."""

    def __init__(
        self,
        mail_connection_repo: MailConnectionRepository,
        account_repo: AccountRepository,
        runner: MailIngestionRunner,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._mail_repo = mail_connection_repo
        self._account_repo = account_repo
        self._runner = runner

    def run_all(
        self,
        *,
        account_ids: list[str] | None = None,
    ) -> MailPollBatchResult:
        """Pollt alle aktiven Mandanten mit konfiguriertem Postfach."""
        active_ids = {a.id for a in self._account_repo.list_by_status("active")}
        pollable = self._mail_repo.list_pollable()
        if account_ids is not None:
            allowed = set(account_ids)
            pollable = [r for r in pollable if r.account_id in allowed]

        summaries: list[AccountPollSummary] = []
        total_processed = 0

        for record in pollable:
            if record.account_id not in active_ids:
                logger.debug(
                    "Skip poll for account %s (not active)",
                    record.account_id,
                )
                continue

            summary = self._poll_account(record.account_id, record.provider)
            summaries.append(summary)
            total_processed += summary.processed
            self._update_connection_status(record.account_id, summary)
            if summary.fetch_error is None:
                self._account_repo.mark_initial_sync_completed(record.account_id)

            logger.info(
                (
                    "Polled account=%s provider=%s processed=%s "
                    "duplicates=%s errors=%s fetch_error=%s"
                ),
                record.account_id,
                record.provider,
                summary.processed,
                summary.duplicates,
                len(summary.item_errors),
                summary.fetch_error,
            )

        return MailPollBatchResult(
            accounts_polled=len(summaries),
            total_processed=total_processed,
            summaries=summaries,
        )

    def _poll_account(self, account_id: str, provider: str) -> AccountPollSummary:
        try:
            result = self._runner.run_for_account(account_id)
        except Exception as exc:
            logger.exception("Fetch failed for account %s", account_id)
            return AccountPollSummary(
                account_id=account_id,
                provider=provider,
                processed=0,
                duplicates=0,
                fetch_error=str(exc),
            )

        item_errors = [item.error for item in result.items if item.error]
        duplicates = sum(1 for item in result.items if item.duplicate)
        return AccountPollSummary(
            account_id=account_id,
            provider=provider,
            processed=result.processed,
            duplicates=duplicates,
            item_errors=item_errors,
        )

    def _update_connection_status(
        self,
        account_id: str,
        summary: AccountPollSummary,
    ) -> None:
        now = datetime.now(UTC)
        if summary.fetch_error:
            self._mail_repo.update_status(
                account_id,
                "error",
                last_error=summary.fetch_error,
            )
            return
        if summary.item_errors:
            self._mail_repo.update_status(
                account_id,
                "connected",
                last_error=summary.item_errors[0],
                last_sync_at=now,
            )
            return
        self._mail_repo.update_status(
            account_id,
            "connected",
            last_error=None,
            last_sync_at=now,
        )


def build_mail_poll_service(
    mail_connection_repo: MailConnectionRepository,
    account_repo: AccountRepository,
    runner: MailIngestionRunner,
) -> MailPollService:
    """Factory für MailPollService."""
    return MailPollService(mail_connection_repo, account_repo, runner)


def build_mail_poll_service_from_context(
    ctx: object, settings: Settings
) -> MailPollService:
    """Erzeugt MailPollService aus AppContext."""
    from backend.core.config.factory import AppContext

    assert isinstance(ctx, AppContext)
    runner = MailIngestionRunner(
        ctx.mail_connection_repo,
        ctx.workflow,
        ctx.email_repo,
        settings,
        ctx.account_repo,
        fetch_max=settings.outlook_fetch_max,
        fetch_unread_only=settings.outlook_fetch_unread_only,
    )
    return MailPollService(ctx.mail_connection_repo, ctx.account_repo, runner)
