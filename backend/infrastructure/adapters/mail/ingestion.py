"""Provider-unabhängiger Mail-Poll → Workflow."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.ai.workflows.email_workflow import EmailWorkflow
from backend.core.config.settings import Settings
from backend.features.mail.ingest_window import filter_messages_for_initial_sync
from backend.infrastructure.adapters.mail.connector import build_mail_connector
from backend.infrastructure.repositories.account_repository import AccountRepository
from backend.infrastructure.repositories.email_repository import EmailRepository
from backend.infrastructure.repositories.mail_connection_repository import (
    MailConnectionRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class MailPollItemResult:
    """Ergebnis einer einzelnen Mail."""

    message_id: str
    ingested: bool
    duplicate: bool
    error: str | None = None


@dataclass
class MailPollRunResult:
    """Gesamtergebnis eines Poll-Laufs."""

    processed: int
    items: list[MailPollItemResult]


class MailIngestionRunner:
    """Holt Mails über MailConnector und startet den Email-Workflow."""

    def __init__(
        self,
        mail_connection_repo: MailConnectionRepository,
        workflow: EmailWorkflow,
        email_repo: EmailRepository,
        settings: Settings,
        account_repo: AccountRepository,
        *,
        fetch_max: int = 100,
        fetch_unread_only: bool = False,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._mail_repo_conn = mail_connection_repo
        self._workflow = workflow
        self._email_repo = email_repo
        self._settings = settings
        self._account_repo = account_repo
        self._fetch_max = fetch_max
        self._fetch_unread_only = fetch_unread_only

    def run_for_account(self, account_id: str) -> MailPollRunResult:
        """Pollt Postfach eines Accounts."""
        record = self._mail_repo_conn.get(account_id)
        if record is None:
            logger.warning("No mail connection for account %s", account_id)
            return MailPollRunResult(processed=0, items=[])
        account = self._account_repo.get_by_id(account_id)
        initial_sync = (
            account is not None and account.mail_initial_sync_completed_at is None
        )
        fetch_limit = self._fetch_max
        if initial_sync and account is not None:
            lookback = account.mail_ingest_lookback_count or (
                self._settings.mail_ingest_initial_lookback
            )
            fetch_limit = min(
                self._settings.mail_ingest_initial_fetch_cap,
                lookback + self._fetch_max,
            )
        connector = build_mail_connector(record, self._settings)
        messages = connector.fetch_messages(
            limit=fetch_limit,
            unread_only=self._fetch_unread_only,
        )
        if initial_sync and account is not None:
            anchor = account.mail_ingest_anchor_at or account.created_at
            lookback = account.mail_ingest_lookback_count or (
                self._settings.mail_ingest_initial_lookback
            )
            messages = filter_messages_for_initial_sync(messages, anchor, lookback)
            logger.info(
                "Initial sync account=%s fetched=%s selected=%s anchor=%s",
                account_id,
                fetch_limit,
                len(messages),
                anchor.isoformat(),
            )
        items: list[MailPollItemResult] = []
        for payload in messages:
            existing = self._email_repo.get_by_message_id(
                payload.message_id,
                account_id=account_id,
            )
            if existing is not None:
                items.append(
                    MailPollItemResult(
                        message_id=payload.message_id,
                        ingested=False,
                        duplicate=True,
                    )
                )
                continue
            try:
                result = self._workflow.run(payload, thread_id=payload.correlation_id)
                duplicate = bool(result.get("ingest_duplicate"))
                items.append(
                    MailPollItemResult(
                        message_id=payload.message_id,
                        ingested=not duplicate,
                        duplicate=duplicate,
                    )
                )
            except Exception as exc:
                logger.exception("Workflow failed for %s", payload.message_id)
                items.append(
                    MailPollItemResult(
                        message_id=payload.message_id,
                        ingested=False,
                        duplicate=False,
                        error=str(exc),
                    )
                )
        processed = sum(1 for item in items if item.ingested)
        return MailPollRunResult(processed=processed, items=items)

    def run_all_pollable(
        self,
        account_ids: list[str] | None = None,
    ) -> dict[str, MailPollRunResult]:
        """Pollt mehrere Accounts (optional gefiltert)."""
        records = self._mail_repo_conn.list_pollable()
        if account_ids is not None:
            allowed = set(account_ids)
            records = [r for r in records if r.account_id in allowed]
        results: dict[str, MailPollRunResult] = {}
        for record in records:
            results[record.account_id] = self.run_for_account(record.account_id)
        return results
