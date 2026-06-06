"""Outlook-Polling und IngestionPort-Adapter."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.ai.services.ingestion import IngestResult
from backend.ai.workflows.email_workflow import EmailWorkflow
from backend.application.ingestion import IngestionPort
from backend.core.config.factory import AppContext
from backend.core.config.settings import Settings
from backend.core.models.email import IncomingEmail
from backend.infrastructure.adapters.outlook.graph import (
    OutlookGraphClient,
    map_graph_message,
)
from backend.infrastructure.repositories.email_repository import EmailRepository

logger = logging.getLogger(__name__)


@dataclass
class PollItemResult:
    """Ergebnis einer einzelnen Mail im Poll-Lauf."""

    message_id: str
    graph_id: str
    ingested: bool
    duplicate: bool
    skipped_existing: bool
    error: str | None = None


@dataclass
class PollRunResult:
    """Gesamtergebnis eines Poll-Laufs."""

    processed: int
    items: list[PollItemResult]


class OutlookIngestionAdapter:
    """IngestionPort für einzelne Mails (z. B. Webhook-Brücke)."""

    def __init__(self, port: IngestionPort) -> None:
        """Initialize the instance with its dependencies."""
        self._port = port

    def ingest_email(self, payload: IncomingEmail) -> IngestResult:
        """Execute the operation."""
        return self._port.ingest_email(payload)


class OutlookIngestionRunner:
    """Holt Inbox-Mails (begrenzt) und startet den Email-Workflow."""

    def __init__(
        self,
        graph: OutlookGraphClient,
        workflow: EmailWorkflow,
        *,
        post_action: str,
        processed_folder: str | None,
        email_repo: EmailRepository,
        fetch_max: int = 100,
        fetch_unread_only: bool = False,
        ingest_account_id: str | None = None,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._graph = graph
        self._workflow = workflow
        self._post_action = post_action
        self._processed_folder = processed_folder
        self._email_repo = email_repo
        self._fetch_max = fetch_max
        self._fetch_unread_only = fetch_unread_only
        self._ingest_account_id = ingest_account_id

    @classmethod
    def from_context(
        cls,
        settings: Settings,
        ctx: AppContext,
    ) -> OutlookIngestionRunner:
        """Execute the operation."""
        graph = OutlookGraphClient.from_settings(settings)
        return cls(
            graph=graph,
            workflow=ctx.workflow,
            post_action=settings.outlook_post_action,
            processed_folder=settings.outlook_processed_folder,
            email_repo=ctx.email_repo,
            fetch_max=settings.outlook_fetch_max,
            fetch_unread_only=settings.outlook_fetch_unread_only,
            ingest_account_id=settings.ingest_account_id,
        )

    def run(
        self, *, top: int | None = None, unread_only: bool | None = None
    ) -> PollRunResult:
        """Run the command workflow."""
        limit = top if top is not None else self._fetch_max
        only_unread = (
            unread_only if unread_only is not None else self._fetch_unread_only
        )
        messages = self._graph.list_inbox_messages(
            limit,
            unread_only=only_unread,
        )
        logger.info(
            "Fetched %s message(s) from inbox (max=%s, unread_only=%s)",
            len(messages),
            limit,
            only_unread,
        )
        items: list[PollItemResult] = []
        mapped: list[tuple[str, IncomingEmail]] = []
        for graph_msg in messages:
            graph_id = str(graph_msg.get("id") or "")
            try:
                payload = map_graph_message(graph_msg)
                if self._ingest_account_id:
                    payload = payload.model_copy(
                        update={"account_id": self._ingest_account_id}
                    )
            except ValueError as exc:
                logger.warning("Skip invalid Graph message %s: %s", graph_id, exc)
                items.append(
                    PollItemResult(
                        message_id="",
                        graph_id=graph_id,
                        ingested=False,
                        duplicate=False,
                        skipped_existing=False,
                        error=str(exc),
                    )
                )
                continue
            mapped.append((graph_id, payload))

        account_id = mapped[0][1].account_id if mapped else self._ingest_account_id
        existing_ids = self._email_repo.find_existing_message_ids(
            [payload.message_id for _, payload in mapped],
            account_id=account_id,
        )
        for graph_id, payload in mapped:
            if payload.message_id in existing_ids:
                items.append(
                    PollItemResult(
                        message_id=payload.message_id,
                        graph_id=graph_id,
                        ingested=False,
                        duplicate=True,
                        skipped_existing=True,
                    )
                )
                continue

            try:
                result = self._workflow.run(
                    payload,
                    thread_id=payload.correlation_id,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Workflow failed for %s", payload.message_id)
                items.append(
                    PollItemResult(
                        message_id=payload.message_id,
                        graph_id=graph_id,
                        ingested=False,
                        duplicate=False,
                        skipped_existing=False,
                        error=str(exc),
                    )
                )
                continue

            duplicate = bool(result.get("ingest_duplicate"))
            items.append(
                PollItemResult(
                    message_id=payload.message_id,
                    graph_id=graph_id,
                    ingested=not duplicate,
                    duplicate=duplicate,
                    skipped_existing=False,
                )
            )
            if graph_id and not duplicate:
                try:
                    self._graph.post_process_message(
                        graph_id,
                        action=self._post_action,
                        processed_folder=self._processed_folder,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Post-process failed for graph_id=%s action=%s: %s",
                        graph_id,
                        self._post_action,
                        exc,
                    )

        ingested_count = sum(1 for i in items if i.ingested)
        return PollRunResult(processed=ingested_count, items=items)
