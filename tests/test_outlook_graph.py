"""Tests für Microsoft Graph Adapter (gemockt, kein Live-API)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.core.config.settings import Settings
from backend.core.models.email import StoredEmail
from backend.infrastructure.adapters.outlook.graph import (
    OutlookGraphClient,
    map_graph_message,
)
from backend.infrastructure.adapters.outlook.ingestion import OutlookIngestionRunner


def _sample_graph_message() -> dict[str, Any]:
    return {
        "id": "graph-msg-1",
        "internetMessageId": "<booking-test@example.com>",
        "subject": "Neue Buchung AB123",
        "from": {"emailAddress": {"address": "guest@example.com", "name": "Guest"}},
        "toRecipients": [
            {"emailAddress": {"address": "host@hotel.example", "name": "Host"}}
        ],
        "receivedDateTime": "2026-06-01T12:00:00Z",
        "body": {"contentType": "text", "content": "Hallo, ich buche AB123."},
        "internetMessageHeaders": [
            {"name": "In-Reply-To", "value": "<parent@example.com>"},
            {"name": "References", "value": "<a@x.com> <b@x.com>"},
        ],
    }


def test_map_graph_message_text_body() -> None:
    """Verify map graph message text body."""
    payload = map_graph_message(_sample_graph_message())
    assert payload.message_id == "<booking-test@example.com>"
    assert payload.from_address == "guest@example.com"
    assert payload.to_addresses == ["host@hotel.example"]
    assert payload.subject == "Neue Buchung AB123"
    assert "AB123" in payload.body_text
    assert payload.body_html is None
    assert payload.in_reply_to == "<parent@example.com>"
    assert payload.references == ["<a@x.com>", "<b@x.com>"]
    assert payload.platform == "outlook"
    assert payload.received_at == datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def test_map_graph_message_html_body() -> None:
    """Verify map graph message html body."""
    msg = _sample_graph_message()
    msg["body"] = {"contentType": "html", "content": "<p>Hi</p>"}
    payload = map_graph_message(msg)
    assert payload.body_text == ""
    assert payload.body_html == "<p>Hi</p>"


def test_map_graph_message_requires_id() -> None:
    """Verify map graph message requires id."""
    with pytest.raises(ValueError, match="internetMessageId"):
        map_graph_message({"receivedDateTime": "2026-06-01T12:00:00Z"})


class _FakeTokenProvider:
    def get_token(self) -> str:
        """Return the requested value."""
        return "fake-token"


class _FakeGraph(OutlookGraphClient):
    def __init__(self, messages: list[dict[str, Any]]) -> None:
        """Initialize the instance with its dependencies."""
        super().__init__(
            auth_mode="delegated",
            mailbox=None,
            token_provider=_FakeTokenProvider(),  # type: ignore[arg-type]
        )
        self._messages = messages
        self.marked: list[str] = []

    def list_inbox_messages(
        self,
        top: int = 100,
        *,
        unread_only: bool = False,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """List matching records."""
        _ = unread_only, since
        return self._messages[:top]

    def list_unread_inbox_messages(self, top: int = 50) -> list[dict[str, Any]]:
        """List matching records."""
        return self.list_inbox_messages(top, unread_only=True)

    def post_process_message(
        self,
        graph_id: str,
        *,
        action: str,
        processed_folder: str | None,
    ) -> None:
        """Execute the operation."""
        self.marked.append(graph_id)


def test_outlook_runner_ingests_and_marks_read(
    ingestion_service,
    email_repo,
    entity_repo,
    extraction_repo,
    embedding_repo,
) -> None:
    """Verify outlook runner ingests and marks read."""
    from tests.test_workflow import _build_workflow

    workflow = _build_workflow(
        ingestion_service,
        email_repo,
        entity_repo,
        extraction_repo,
        embedding_repo,
    )
    graph_msg = _sample_graph_message()
    graph = _FakeGraph([graph_msg])
    runner = OutlookIngestionRunner(
        graph=graph,
        workflow=workflow,
        post_action="mark_read",
        processed_folder=None,
        email_repo=email_repo,
    )
    result = runner.run()
    assert result.processed == 1
    assert graph.marked == ["graph-msg-1"]
    stored = email_repo.get_by_message_id("<booking-test@example.com>")
    assert stored is not None


def test_outlook_runner_skips_existing_message_id(
    ingestion_service,
    email_repo,
    booking_emails,
) -> None:
    """Verify outlook runner skips existing message id."""
    from tests.test_workflow import _build_workflow

    workflow = _build_workflow(
        ingestion_service,
        email_repo,
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    existing = StoredEmail(
        **booking_emails[0].model_dump(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    email_repo.upsert_by_message_id(existing)

    graph_msg = _sample_graph_message()
    graph_msg["internetMessageId"] = booking_emails[0].message_id
    graph = _FakeGraph([graph_msg])
    runner = OutlookIngestionRunner(
        graph=graph,
        workflow=workflow,
        post_action="mark_read",
        processed_folder=None,
        email_repo=email_repo,
    )
    result = runner.run()
    assert result.processed == 0
    assert result.items[0].skipped_existing is True
    assert graph.marked == []


@patch("backend.infrastructure.adapters.outlook.graph.urlopen")
def test_graph_client_list_unread(mock_urlopen: MagicMock) -> None:
    """Verify graph client list unread."""
    body = json.dumps({"value": [_sample_graph_message()]}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    client = OutlookGraphClient(
        auth_mode="delegated",
        mailbox=None,
        token_provider=_FakeTokenProvider(),  # type: ignore[arg-type]
    )
    client._token = "t"  # noqa: SLF001
    messages = client.list_unread_inbox_messages(top=5)
    assert len(messages) == 1
    req = mock_urlopen.call_args[0][0]
    assert "mailFolders/inbox/messages" in req.full_url
    assert "isRead" in req.full_url


@patch("backend.infrastructure.adapters.outlook.graph.urlopen")
def test_graph_client_list_inbox_since_filter(mock_urlopen: MagicMock) -> None:
    """Graph-Poll nutzt receivedDateTime-Filter für zuverlässiges $orderby."""
    body = json.dumps({"value": [_sample_graph_message()]}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    client = OutlookGraphClient(
        auth_mode="delegated",
        mailbox=None,
        token_provider=_FakeTokenProvider(),  # type: ignore[arg-type]
    )
    client._token = "t"  # noqa: SLF001
    since = datetime(2026, 6, 5, 0, 0, tzinfo=UTC)
    messages = client.list_inbox_messages(top=10, since=since)
    assert len(messages) == 1
    req = mock_urlopen.call_args[0][0]
    assert "receivedDateTime+ge+2026-06-05T00%3A00%3A00Z" in req.full_url
    assert "receivedDateTime+desc" in req.full_url


def test_outlook_graph_client_from_settings_delegated() -> None:
    """Verify outlook graph client from settings delegated."""
    settings = Settings.model_validate(
        {
            "OPENAI_API_KEY": "sk-test",
            "MONGODB_URI": "mongodb://localhost",
            "LANGFUSE_PUBLIC_KEY": "pk",
            "LANGFUSE_SECRET_KEY": "sk",
            "AZURE_CLIENT_ID": "client-id",
            "OUTLOOK_AUTH_MODE": "delegated",
        }
    )
    client = OutlookGraphClient.from_settings(settings)
    assert client._auth_mode == "delegated"  # noqa: SLF001


def test_outlook_graph_client_from_settings_application_requires_mailbox() -> None:
    """Verify outlook graph client from settings application requires mailbox."""
    settings = Settings.model_validate(
        {
            "OPENAI_API_KEY": "sk-test",
            "MONGODB_URI": "mongodb://localhost",
            "LANGFUSE_PUBLIC_KEY": "pk",
            "LANGFUSE_SECRET_KEY": "sk",
            "AZURE_CLIENT_ID": "c",
            "AZURE_TENANT_ID": "t",
            "AZURE_CLIENT_SECRET": "s",
            "OUTLOOK_AUTH_MODE": "application",
            "OUTLOOK_MAILBOX": "",
        }
    )
    with pytest.raises(ValueError, match="OUTLOOK_MAILBOX"):
        OutlookGraphClient.from_settings(settings)


@pytest.mark.live_graph
def test_live_graph_smoke() -> None:
    """Manueller Smoke-Test mit echter .env – nicht in CI."""
    from backend.core.config.settings import get_settings

    settings = get_settings()
    if not settings.azure_client_id:
        pytest.skip("AZURE_CLIENT_ID not set")
    client = OutlookGraphClient.from_settings(settings)
    messages = client.list_unread_inbox_messages(top=1)
    assert isinstance(messages, list)
