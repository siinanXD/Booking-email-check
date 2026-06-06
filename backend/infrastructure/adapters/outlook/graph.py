"""Microsoft Graph REST client for Outlook mail."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from backend.core.config.settings import Settings
from backend.infrastructure.adapters.outlook.auth import (
    ApplicationAuth,
    CachedDelegatedAuth,
    DelegatedAuth,
)
from backend.infrastructure.adapters.outlook.message_mapper import map_graph_message
from backend.infrastructure.adapters.outlook.poll_window import format_graph_datetime
from backend.infrastructure.repositories.mail_connection_repository import (
    MailConnectionRecord,
)

logger = logging.getLogger(__name__)

TokenProvider = DelegatedAuth | ApplicationAuth | CachedDelegatedAuth

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
_MESSAGE_SELECT = (
    "id,internetMessageId,subject,from,toRecipients,receivedDateTime,"
    "body,internetMessageHeaders"
)

__all__ = ["OutlookGraphClient", "map_graph_message"]


class OutlookGraphClient:
    """Graph REST-Client für Inbox-Ungelesen und Nachbearbeitung."""

    def __init__(
        self,
        *,
        auth_mode: str,
        mailbox: str | None,
        token_provider: TokenProvider,
    ) -> None:
        mode = auth_mode.strip().lower()
        if mode not in ("delegated", "application", "oauth"):
            msg = f"Unsupported OUTLOOK_AUTH_MODE: {auth_mode}"
            raise ValueError(msg)
        self._auth_mode = mode
        self._mailbox = mailbox
        self._token_provider = token_provider
        self._token: str | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> OutlookGraphClient:
        if not settings.azure_client_id:
            msg = "AZURE_CLIENT_ID is required for Outlook ingestion"
            raise ValueError(msg)
        mode = settings.outlook_auth_mode.strip().lower()
        if mode == "application":
            if not settings.azure_tenant_id:
                msg = "AZURE_TENANT_ID is required for application auth"
                raise ValueError(msg)
            if not settings.azure_client_secret:
                msg = "AZURE_CLIENT_SECRET is required for application auth"
                raise ValueError(msg)
            if not settings.outlook_mailbox:
                msg = "OUTLOOK_MAILBOX is required for application auth"
                raise ValueError(msg)
            token_provider: DelegatedAuth | ApplicationAuth = ApplicationAuth(
                settings.azure_tenant_id,
                settings.azure_client_id,
                settings.azure_client_secret,
            )
        else:
            token_provider = DelegatedAuth(
                settings.azure_client_id,
                settings.azure_authority,
                Path(settings.outlook_token_cache_path),
            )
        return cls(
            auth_mode=mode,
            mailbox=settings.outlook_mailbox,
            token_provider=token_provider,
        )

    @classmethod
    def from_mail_record(
        cls,
        record: MailConnectionRecord,
        settings: Settings,
    ) -> OutlookGraphClient:
        """Graph-Client aus Mandanten-Postfach-Konfiguration."""
        if not settings.azure_client_id:
            msg = "AZURE_CLIENT_ID is required for Outlook ingestion"
            raise ValueError(msg)
        mode = (record.outlook_auth_mode or "application").strip().lower()
        mailbox = record.outlook_mailbox.strip() or record.email_address.strip() or None
        if mode == "oauth":
            if not record.outlook_token_cache.strip():
                msg = "Outlook OAuth ist nicht verbunden"
                raise ValueError(msg)
            if not settings.azure_client_secret:
                msg = "AZURE_CLIENT_SECRET is required for OAuth"
                raise ValueError(msg)
            token_provider: TokenProvider = CachedDelegatedAuth(
                settings.azure_client_id,
                settings.azure_authority,
                settings.azure_client_secret,
                record.outlook_token_cache,
            )
            return cls(
                auth_mode="oauth", mailbox=mailbox, token_provider=token_provider
            )
        if mode == "application":
            if not settings.azure_tenant_id:
                msg = "AZURE_TENANT_ID is required for application auth"
                raise ValueError(msg)
            if not settings.azure_client_secret:
                msg = "AZURE_CLIENT_SECRET is required for application auth"
                raise ValueError(msg)
            if not mailbox:
                msg = "Outlook mailbox is required for application auth"
                raise ValueError(msg)
            token_provider = ApplicationAuth(
                settings.azure_tenant_id,
                settings.azure_client_id,
                settings.azure_client_secret,
            )
            return cls(
                auth_mode="application", mailbox=mailbox, token_provider=token_provider
            )
        token_provider = DelegatedAuth(
            settings.azure_client_id,
            settings.azure_authority,
            Path(settings.outlook_token_cache_path),
        )
        return cls(
            auth_mode="delegated", mailbox=mailbox, token_provider=token_provider
        )

    def _resource_prefix(self) -> str:
        if self._auth_mode == "application":
            assert self._mailbox
            return f"users/{quote(self._mailbox, safe='')}"
        return "me"

    def _access_token(self) -> str:
        if self._token is None:
            self._token = self._token_provider.get_token()
        return self._token

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        query = f"?{urlencode(params)}" if params else ""
        url = f"{GRAPH_ROOT}/{path.lstrip('/')}{query}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {
            "Authorization": f"Bearer {self._access_token()}",
            "Accept": "application/json",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return {}
                return cast(dict[str, Any], json.loads(raw))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Graph {method} {path} failed ({exc.code}): {detail}"
            ) from exc

    def list_inbox_messages(
        self,
        top: int = 100,
        *,
        unread_only: bool = False,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        prefix = self._resource_prefix()
        params: dict[str, str] = {
            "$top": str(top),
            "$select": _MESSAGE_SELECT,
            "$orderby": "receivedDateTime desc",
        }
        filters: list[str] = []
        if unread_only:
            filters.append("isRead eq false")
        if since is not None:
            filters.append(f"receivedDateTime ge {format_graph_datetime(since)}")
        if filters:
            params["$filter"] = " and ".join(filters)
        path = f"{prefix}/mailFolders/inbox/messages"
        payload = self._request("GET", path, params=params)
        return list(payload.get("value") or [])

    def list_unread_inbox_messages(self, top: int = 50) -> list[dict[str, Any]]:
        return self.list_inbox_messages(top, unread_only=True)

    def mark_message_read(self, graph_id: str) -> None:
        prefix = self._resource_prefix()
        path = f"{prefix}/messages/{quote(graph_id, safe='')}"
        self._request("PATCH", path, body={"isRead": True})

    def move_message_to_folder(self, graph_id: str, folder_display_name: str) -> None:
        folder_id = self._resolve_folder_id(folder_display_name)
        prefix = self._resource_prefix()
        path = f"{prefix}/messages/{quote(graph_id, safe='')}/move"
        self._request("POST", path, body={"destinationId": folder_id})

    def _resolve_folder_id(self, display_name: str) -> str:
        prefix = self._resource_prefix()
        params = {"$filter": f"displayName eq '{display_name}'", "$select": "id"}
        payload = self._request("GET", f"{prefix}/mailFolders", params=params)
        folders = payload.get("value") or []
        if not folders:
            msg = f"Mail folder not found: {display_name}"
            raise ValueError(msg)
        return str(folders[0]["id"])

    def post_process_message(
        self,
        graph_id: str,
        *,
        action: str,
        processed_folder: str | None,
    ) -> None:
        act = action.strip().lower()
        if act in ("", "none", "skip"):
            return
        if act == "move":
            if not processed_folder:
                msg = "OUTLOOK_PROCESSED_FOLDER required when OUTLOOK_POST_ACTION=move"
                raise ValueError(msg)
            self.move_message_to_folder(graph_id, processed_folder)
            return
        if act == "mark_read":
            self.mark_message_read(graph_id)
            return
        msg = f"Unsupported OUTLOOK_POST_ACTION: {action!r} (use none, mark_read, move)"
        raise ValueError(msg)
