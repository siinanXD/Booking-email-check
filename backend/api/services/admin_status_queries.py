"""Admin-System-Status-Ampel (DB, Polling, WhatsApp, Konten, Integrationen)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from backend.api.schemas.admin_status import (
    AdminStatusResponse,
    StatusAccounts,
    StatusDb,
    StatusIntegrations,
    StatusPolling,
    StatusWhatsApp,
)
from backend.api.services._status_health import poll_stale
from backend.core.config.factory import AppContext
from backend.core.config.settings import Settings


def _db_ok(ctx: AppContext) -> bool:
    try:
        ctx.email_repo._col.database.command("ping")
    except Exception:  # noqa: BLE001 - Ping-Fehler = DB nicht erreichbar
        return False
    return True


def _overall(
    db_ok: bool, stale: bool, account_errors: int, wa_failed: int
) -> Literal["ok", "degraded", "down"]:
    if not db_ok:
        return "down"
    if stale or account_errors > 0 or wa_failed > 0:
        return "degraded"
    return "ok"


def admin_status(ctx: AppContext, settings: Settings) -> AdminStatusResponse:
    """Punktueller System-Status für die Ampel."""
    now = datetime.now(UTC)
    db_ok = _db_ok(ctx)

    conn_repo = ctx.mail_connection_repo
    newest = conn_repo.newest_sync_at()
    expected = conn_repo.has_pollable()
    stale = poll_stale(
        newest,
        expected=expected,
        now=now,
        threshold_seconds=settings.poll_heartbeat_stale_seconds,
    )
    connections = conn_repo.list_all()
    connected = sum(1 for c in connections if c.status == "connected")
    errors = sum(1 for c in connections if c.status == "error")

    since_24h = (now - timedelta(hours=24)).isoformat()
    wa = ctx.notification_repo.count_by_status(since_24h)
    wa_failed = int(wa.get("failed", 0))

    return AdminStatusResponse(
        db=StatusDb(ok=db_ok),
        polling=StatusPolling(
            expected=expected,
            stale=stale,
            last_sync_at=newest.isoformat() if newest else None,
            pollable_accounts=len(conn_repo.list_pollable()),
        ),
        whatsapp_24h=StatusWhatsApp(
            sent=int(wa.get("sent", 0)),
            failed=wa_failed,
            skipped=int(wa.get("skipped", 0)),
            pending=int(wa.get("pending", 0)),
        ),
        accounts=StatusAccounts(
            connected=connected, error=errors, total=len(connections)
        ),
        integrations=StatusIntegrations(
            langfuse_configured=bool(
                settings.langfuse_public_key and settings.langfuse_secret_key
            ),
            sentry_configured=bool(settings.sentry_dsn),
        ),
        overall=_overall(db_ok, stale, errors, wa_failed),
    )
