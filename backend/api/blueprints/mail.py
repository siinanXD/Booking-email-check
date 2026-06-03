"""Postfach-Verbindung API."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, g, jsonify, redirect, request

from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.roles import is_account_admin
from backend.api.middleware.tenant import get_request_account_id, require_account
from backend.api.schemas.mail import (
    MailConnectionUpdate,
    MailSyncResponse,
    MailTestResponse,
)
from backend.features.mail.mail_connection_service import MailConnectionService
from backend.features.mail.mail_poll_service import (
    AccountPollSummary,
    build_mail_poll_service_from_context,
)
from backend.features.mail.mail_reprocess_service import (
    MailReprocessResult,
    build_mail_reprocess_service,
)
from backend.features.mail.outlook_oauth_service import OutlookOAuthService
from backend.infrastructure.repositories.mail_connection_repository import (
    MailConnectionRepository,
)

mail_bp = Blueprint("mail", __name__, url_prefix="/api/mail")


def _require_admin() -> tuple[Any, int] | None:
    role = g.current_user.get("role")
    if not is_account_admin(role):
        return jsonify({"error": "Admin required", "code": 403}), 403
    return None


def _service() -> MailConnectionService:
    return MailConnectionService(
        g.ctx.mail_connection_repo,
        g.ctx.platform_settings_repo,
        g.settings,
    )


def _oauth_service() -> OutlookOAuthService:
    return OutlookOAuthService(
        g.settings,
        g.ctx.mail_connection_repo,
        g.ctx.outlook_oauth_flow_repo,
    )


def _sync_reprocess_requested() -> bool:
    value = request.args.get("reprocess", "").strip().lower()
    return value in {"1", "true", "yes"}


def _build_sync_response(
    account_id: str,
    summary: AccountPollSummary,
    *,
    reprocess: MailReprocessResult | None = None,
) -> tuple[Any, int]:
    reprocess = reprocess or MailReprocessResult()
    updated = g.ctx.mail_connection_repo.get(account_id)
    last_sync = (
        updated.last_sync_at.isoformat() if updated and updated.last_sync_at else None
    )
    item_errors = [err for err in summary.item_errors if err]
    reprocess_errors = list(reprocess.errors)
    error_count = len(item_errors) + len(reprocess_errors)
    reprocessed = reprocess.completed
    if error_count:
        message = (
            f"{summary.processed} neue Mail(s), {summary.duplicates} Duplikat(e), "
            f"{reprocessed} nachverarbeitet, {error_count} Fehler."
        )
    else:
        message = (
            f"{summary.processed} neue Mail(s) verarbeitet, "
            f"{summary.duplicates} bereits bekannt"
            + (f", {reprocessed} nachverarbeitet" if reprocessed else "")
            + "."
        )
    return (
        jsonify(
            MailSyncResponse(
                success=error_count == 0,
                processed=summary.processed,
                duplicates=summary.duplicates,
                error_count=error_count,
                reprocessed=reprocessed,
                message=message,
                last_sync_at=last_sync,
                item_errors=item_errors,
                reprocess_errors=reprocess_errors,
            ).model_dump()
        ),
        200,
    )


@mail_bp.get("/connection")
@require_auth
@require_account
def get_connection() -> tuple[Any, int]:
    """Lädt Postfach-Konfiguration des Accounts."""
    denied = _require_admin()
    if denied:
        return denied
    account_id = get_request_account_id()
    assert account_id
    return jsonify(_service().get_response(account_id).model_dump()), 200


@mail_bp.put("/connection")
@require_auth
@require_account
def update_connection() -> tuple[Any, int]:
    """Speichert Postfach-Konfiguration."""
    denied = _require_admin()
    if denied:
        return denied
    account_id = get_request_account_id()
    assert account_id
    body = MailConnectionUpdate.model_validate(request.get_json(silent=True) or {})
    response = _service().apply_update(account_id, body)
    return jsonify(response.model_dump()), 200


@mail_bp.post("/sync")
@require_auth
@require_account
def sync_mailbox() -> tuple[Any, int]:
    """Holt neue Mails aus dem Postfach und startet die Verarbeitung."""
    denied = _require_admin()
    if denied:
        return denied
    account_id = get_request_account_id()
    assert account_id
    record = g.ctx.mail_connection_repo.get(account_id)
    if record is None or not MailConnectionRepository.is_pollable(record):
        return (
            jsonify(
                MailSyncResponse(
                    success=False,
                    message=(
                        "Postfach ist nicht bereit zum Abruf. "
                        "Onboarding abschließen und Verbindung testen."
                    ),
                ).model_dump()
            ),
            400,
        )
    poll = build_mail_poll_service_from_context(g.ctx, g.settings)
    result = poll.run_all(account_ids=[account_id])
    reprocess = MailReprocessResult()
    if _sync_reprocess_requested():
        reprocess = build_mail_reprocess_service(g.ctx).reprocess_stuck_bookings(
            account_id,
            limit=25,
        )
    summary = result.summaries[0] if result.summaries else None
    if summary is None:
        return (
            jsonify(
                MailSyncResponse(
                    success=False,
                    message="Kein aktiver Account zum Abruf gefunden.",
                ).model_dump()
            ),
            400,
        )
    if summary.fetch_error:
        item_errors = [err for err in summary.item_errors if err]
        return (
            jsonify(
                MailSyncResponse(
                    success=False,
                    processed=summary.processed,
                    duplicates=summary.duplicates,
                    error_count=len(item_errors),
                    message=f"Postfach-Abruf fehlgeschlagen: {summary.fetch_error}",
                    item_errors=item_errors,
                ).model_dump()
            ),
            502,
        )
    return _build_sync_response(account_id, summary, reprocess=reprocess)


@mail_bp.post("/test")
@require_auth
@require_account
def test_connection() -> tuple[Any, int]:
    """Testet die gespeicherte Postfach-Verbindung."""
    denied = _require_admin()
    if denied:
        return denied
    account_id = get_request_account_id()
    assert account_id
    result = _service().test_connection(account_id)
    status = 200 if result.success else 502
    return (
        jsonify(
            MailTestResponse(
                success=result.success,
                message=result.message,
                mailbox_count=result.mailbox_count,
            ).model_dump()
        ),
        status,
    )


@mail_bp.get("/outlook/authorize-url")
@require_auth
@require_account
def get_outlook_authorize_url() -> tuple[Any, int]:
    """OAuth-Login-URL für Browser-Redirect (Microsoft)."""
    denied = _require_admin()
    if denied:
        return denied
    account_id = get_request_account_id()
    assert account_id
    return_to = request.args.get("return_to", "/onboarding")
    frontend_origin = request.args.get("frontend_origin", "")
    try:
        url = _oauth_service().build_authorize_url(
            account_id,
            return_to,
            frontend_origin,
        )
    except (ValueError, RuntimeError) as exc:
        return jsonify({"error": str(exc), "code": 400}), 400
    redirect_uri = g.settings.outlook_oauth_redirect_uri
    return (
        jsonify(
            {
                "authorize_url": url,
                "redirect_uri": redirect_uri,
                "azure_client_id": g.settings.azure_client_id,
            }
        ),
        200,
    )


@mail_bp.get("/outlook/oauth-config")
def get_outlook_oauth_config() -> tuple[Any, int]:
    """Dev-Hilfe: zeigt die vom laufenden Backend genutzte OAuth-Konfiguration."""
    if g.settings.app_env != "development":
        return jsonify({"error": "Not found", "code": 404}), 404
    return (
        jsonify(
            {
                "redirect_uri": g.settings.outlook_oauth_redirect_uri,
                "azure_client_id": g.settings.azure_client_id,
                "flask_port": g.settings.flask_port,
                "env_redirect_raw": g.settings.outlook_oauth_redirect_uri_env,
            }
        ),
        200,
    )


@mail_bp.get("/outlook/callback")
def outlook_oauth_callback() -> Any:
    """Microsoft OAuth Callback – tauscht Code, leitet ins Frontend weiter."""
    return complete_outlook_oauth_callback()


def complete_outlook_oauth_callback() -> Any:
    """Shared handler für /api/mail/outlook/callback und /api/msal/callback."""
    query = {key: request.args.get(key, "") for key in request.args}
    redirect_url, _error = _oauth_service().complete_callback(query)
    return redirect(redirect_url)
