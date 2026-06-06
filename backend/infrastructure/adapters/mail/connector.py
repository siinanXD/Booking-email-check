"""Mail-Connector-Abstraktion (Outlook Graph + IMAP)."""

from __future__ import annotations

import email
import imaplib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Protocol

from backend.core.config.settings import Settings
from backend.core.models.email import IncomingEmail
from backend.infrastructure.adapters.outlook.graph import (
    OutlookGraphClient,
    map_graph_message,
)
from backend.infrastructure.repositories.mail_connection_repository import (
    MailConnectionRecord,
)

logger = logging.getLogger(__name__)


@dataclass
class MailTestResult:
    """Ergebnis eines Verbindungstests."""

    success: bool
    message: str
    mailbox_count: int | None = None


class MailConnector(Protocol):
    """Port für Postfach-Abruf und Verbindungstest."""

    def test_connection(self) -> MailTestResult:
        """Prüft Zugangsdaten."""
        ...

    def fetch_messages(
        self,
        *,
        limit: int = 10,
        unread_only: bool = False,
        since: datetime | None = None,
    ) -> list[IncomingEmail]:
        """Holt Nachrichten aus dem Posteingang."""
        ...


def build_mail_connector(
    record: MailConnectionRecord,
    settings: Settings,
) -> MailConnector:
    """Factory für den konfigurierten Provider."""
    if record.provider == "outlook":
        return OutlookMailConnector(record, settings)
    return ImapMailConnector(record)


class OutlookMailConnector:
    """Microsoft Graph / Outlook."""

    def __init__(self, record: MailConnectionRecord, settings: Settings) -> None:
        self._record = record
        self._settings = settings

    def _client(self) -> OutlookGraphClient:
        return OutlookGraphClient.from_mail_record(self._record, self._settings)

    def test_connection(self) -> MailTestResult:
        try:
            client = self._client()
            messages = client.list_inbox_messages(1, unread_only=False)
            count = len(messages)
            return MailTestResult(
                success=True,
                message="Outlook-Verbindung erfolgreich.",
                mailbox_count=count,
            )
        except Exception as exc:
            logger.exception("Outlook test failed")
            return MailTestResult(success=False, message=str(exc))

    def fetch_messages(
        self,
        *,
        limit: int = 10,
        unread_only: bool = False,
        since: datetime | None = None,
    ) -> list[IncomingEmail]:
        client = self._client()
        raw_messages = client.list_inbox_messages(
            limit,
            unread_only=unread_only,
            since=since,
        )
        result: list[IncomingEmail] = []
        for graph_msg in raw_messages:
            mapped = map_graph_message(graph_msg)
            result.append(
                mapped.model_copy(
                    update={"account_id": self._record.account_id},
                )
            )
        return result


def _decode_mime_header(value: str | None) -> str:
    if not value:
        return ""
    parts: list[str] = []
    for chunk, charset in decode_header(value):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(chunk)
    return "".join(parts)


def _extract_body(msg: email.message.Message) -> tuple[str, str | None]:
    body_text = ""
    body_html: str | None = None
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if "attachment" in disposition:
                continue
            payload = part.get_payload(decode=True)
            if payload is None or not isinstance(payload, bytes):
                continue
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if content_type == "text/plain" and not body_text:
                body_text = text
            elif content_type == "text/html" and body_html is None:
                body_html = text
    else:
        payload = msg.get_payload(decode=True)
        if isinstance(payload, bytes):
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                body_html = text
            else:
                body_text = text
    return body_text, body_html


class ImapMailConnector:
    """Generischer IMAP-Connector (GMX, Web.de, Gmail, …)."""

    def __init__(self, record: MailConnectionRecord) -> None:
        self._record = record

    def _connect(self) -> imaplib.IMAP4:
        host = self._record.imap_host.strip()
        if not host:
            msg = "IMAP-Host fehlt"
            raise ValueError(msg)
        if self._record.imap_use_ssl:
            client: imaplib.IMAP4 = imaplib.IMAP4_SSL(host, self._record.imap_port)
        else:
            client = imaplib.IMAP4(host, self._record.imap_port)
        username = self._record.imap_username.strip() or self._record.email_address
        password = self._record.imap_password
        if not username or not password:
            msg = "IMAP-Benutzername oder Passwort fehlt"
            raise ValueError(msg)
        client.login(username, password)
        return client

    def test_connection(self) -> MailTestResult:
        try:
            client = self._connect()
            status, data = client.select("INBOX", readonly=True)
            if status != "OK":
                return MailTestResult(
                    success=False, message="INBOX konnte nicht geöffnet werden."
                )
            count = int(data[0]) if data and data[0] else 0
            client.logout()
            return MailTestResult(
                success=True,
                message="IMAP-Verbindung erfolgreich.",
                mailbox_count=count,
            )
        except Exception as exc:
            logger.exception("IMAP test failed")
            return MailTestResult(success=False, message=str(exc))

    def fetch_messages(
        self,
        *,
        limit: int = 10,
        unread_only: bool = False,
        since: datetime | None = None,
    ) -> list[IncomingEmail]:
        _ = since  # IMAP: kein serverseitiges Datumsfilter in MVP
        client = self._connect()
        try:
            client.select("INBOX", readonly=True)
            criterion = "UNSEEN" if unread_only else "ALL"
            status, data = client.search(None, criterion)
            if status != "OK" or not data or not data[0]:
                return []
            ids = data[0].split()
            selected = ids[-limit:] if limit else ids
            messages: list[IncomingEmail] = []
            for msg_id in reversed(selected):
                status, fetched = client.fetch(msg_id, "(RFC822)")
                if status != "OK" or not fetched or not fetched[0]:
                    continue
                raw = fetched[0][1]
                if not isinstance(raw, bytes):
                    continue
                parsed = email.message_from_bytes(raw)
                message_id = parsed.get("Message-ID") or f"imap-{msg_id.decode()}"
                from_addr = _decode_mime_header(parsed.get("From"))
                subject = _decode_mime_header(parsed.get("Subject"))
                body_text, body_html = _extract_body(parsed)
                received_raw = parsed.get("Date")
                received_at = (
                    parsedate_to_datetime(received_raw).astimezone(UTC)
                    if received_raw
                    else datetime.now(UTC)
                )
                in_reply_to = parsed.get("In-Reply-To")
                references_raw = parsed.get("References") or ""
                references = [r for r in references_raw.split() if r]
                messages.append(
                    IncomingEmail(
                        message_id=message_id.strip(),
                        from_address=from_addr,
                        to_addresses=[],
                        subject=subject,
                        body_text=body_text,
                        body_html=body_html,
                        received_at=received_at,
                        in_reply_to=in_reply_to,
                        references=references,
                        platform="imap",
                        account_id=self._record.account_id,
                    )
                )
            return messages
        finally:
            try:
                client.logout()
            except Exception:
                pass
