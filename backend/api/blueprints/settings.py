"""Persistente Plattform-Einstellungen und Mandanten-API-Helfer."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, g, jsonify, request

from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.roles import is_account_admin
from backend.api.middleware.tenant import get_request_account_id, require_account
from backend.api.schemas.settings import (
    PlatformSettingsResponse,
    PlatformSettingsUpdate,
    PropertyRecipientItem,
    UserProfileSettings,
    WhatsAppTestRequest,
    WhatsAppTestResponse,
    WipeDataResponse,
)
from backend.features.notifications.whatsapp_client import (
    send_whatsapp_hello_world_test,
)
from backend.features.platform.data_wipe_service import DataWipeService
from backend.features.platform.effective_settings import (
    display_platform_settings,
    merge_platform_settings,
    platform_from_env,
)
from backend.infrastructure.observability.langfuse_wipe import LangfuseWipeService
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRecord,
)

settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")


def _require_admin() -> tuple[Any, int] | None:
    role = g.current_user.get("role")
    if not is_account_admin(role):
        return jsonify({"error": "Admin required", "code": 403}), 403
    return None


def _account_id() -> str:
    account_id = get_request_account_id()
    assert account_id
    return account_id


def _display_platform() -> PlatformSettingsRecord:
    ctx = g.ctx
    stored = ctx.platform_settings_repo.get(_account_id())
    return display_platform_settings(g.settings, stored)


def _to_response() -> PlatformSettingsResponse:
    ctx = g.ctx
    account_id = _account_id()
    platform = _display_platform()
    user = ctx.user_repo.get_by_id(str(g.current_user["id"]))
    props = ctx.property_recipient_repo.list_all(account_id)
    profile = UserProfileSettings()
    if user is not None:
        profile = UserProfileSettings(
            whatsapp_phone_e164=user.whatsapp_phone_e164,
            whatsapp_enabled=user.whatsapp_enabled,
        )
    return PlatformSettingsResponse(
        whatsapp_enabled=platform.whatsapp_enabled,
        whatsapp_access_token_set=bool(
            platform.whatsapp_access_token.strip()
            or g.settings.whatsapp_access_token.strip()
        ),
        whatsapp_phone_number_id=platform.whatsapp_phone_number_id,
        whatsapp_api_version=platform.whatsapp_api_version,
        whatsapp_template_language=platform.whatsapp_template_language,
        whatsapp_template_cleaning_task=platform.whatsapp_template_cleaning_task,
        whatsapp_template_status_notice=platform.whatsapp_template_status_notice,
        whatsapp_template_guest_inquiry=platform.whatsapp_template_guest_inquiry,
        whatsapp_default_recipients=platform.whatsapp_default_recipients,
        whatsapp_test_recipient=platform.whatsapp_test_recipient,
        outlook_mailbox=platform.outlook_mailbox,
        property_recipients=[
            PropertyRecipientItem(
                property_name=p.property_name,
                employees=list(p.employees),
            )
            for p in props
        ],
        user_profile=profile,
    )


@settings_bp.get("")
@require_auth
@require_account
def get_settings() -> tuple[Any, int]:
    """Lädt alle Einstellungen (Token maskiert)."""
    denied = _require_admin()
    if denied:
        return denied
    return jsonify(_to_response().model_dump()), 200


@settings_bp.put("")
@require_auth
@require_account
def update_settings() -> tuple[Any, int]:
    """Speichert Einstellungen dauerhaft in MongoDB."""
    denied = _require_admin()
    if denied:
        return denied
    body = PlatformSettingsUpdate.model_validate(request.get_json(silent=True) or {})
    ctx = g.ctx
    account_id = _account_id()
    current = ctx.platform_settings_repo.get(account_id)
    if current is None:
        current = platform_from_env(g.settings, account_id)

    if body.whatsapp_enabled is not None:
        current.whatsapp_enabled = body.whatsapp_enabled
    if body.whatsapp_access_token is not None and body.whatsapp_access_token.strip():
        current.whatsapp_access_token = body.whatsapp_access_token.strip()
    if body.whatsapp_phone_number_id is not None:
        current.whatsapp_phone_number_id = body.whatsapp_phone_number_id.strip()
    if body.whatsapp_api_version is not None:
        current.whatsapp_api_version = body.whatsapp_api_version.strip()
    if body.whatsapp_template_language is not None:
        current.whatsapp_template_language = body.whatsapp_template_language.strip()
    if body.whatsapp_template_cleaning_task is not None:
        current.whatsapp_template_cleaning_task = (
            body.whatsapp_template_cleaning_task.strip()
        )
    if body.whatsapp_template_status_notice is not None:
        current.whatsapp_template_status_notice = (
            body.whatsapp_template_status_notice.strip()
        )
    if body.whatsapp_template_guest_inquiry is not None:
        current.whatsapp_template_guest_inquiry = (
            body.whatsapp_template_guest_inquiry.strip()
        )
    if body.whatsapp_default_recipients is not None:
        current.whatsapp_default_recipients = body.whatsapp_default_recipients.strip()
    if body.whatsapp_test_recipient is not None:
        current.whatsapp_test_recipient = body.whatsapp_test_recipient.strip()
    if body.outlook_mailbox is not None:
        current.outlook_mailbox = body.outlook_mailbox.strip()

    ctx.platform_settings_repo.save(current)

    if body.property_recipients is not None:
        ctx.property_recipient_repo.replace_all(
            account_id,
            [
                (item.property_name, item.normalized_employees)
                for item in body.property_recipients
            ],
        )

    if body.user_profile is not None:
        ctx.user_repo.update_whatsapp_profile(
            str(g.current_user["id"]),
            whatsapp_phone_e164=body.user_profile.whatsapp_phone_e164,
            whatsapp_enabled=body.user_profile.whatsapp_enabled,
        )

    return jsonify(_to_response().model_dump()), 200


@settings_bp.post("/whatsapp/test")
@require_auth
@require_account
def test_whatsapp() -> tuple[Any, int]:
    """Sendet Meta hello_world an Test-Empfänger."""
    denied = _require_admin()
    if denied:
        return denied
    body = WhatsAppTestRequest.model_validate(request.get_json(silent=True) or {})
    ctx = g.ctx
    account_id = _account_id()
    platform = ctx.platform_settings_repo.get(account_id)
    effective = merge_platform_settings(g.settings, platform)
    recipient = (
        body.recipient_e164
        or (platform.whatsapp_test_recipient if platform else "")
        or g.settings.whatsapp_test_recipient
        or ""
    ).strip()
    if not recipient:
        return (
            jsonify(
                WhatsAppTestResponse(
                    success=False,
                    error="Keine Test-Nummer konfiguriert (whatsapp_test_recipient).",
                ).model_dump()
            ),
            400,
        )
    result = send_whatsapp_hello_world_test(effective, recipient)
    return (
        jsonify(
            WhatsAppTestResponse(
                success=result.success,
                provider_message_id=result.provider_message_id,
                error=result.error,
            ).model_dump()
        ),
        200,
    )


@settings_bp.post("/wipe-all")
@require_auth
@require_account
def wipe_all_data() -> tuple[Any, int]:
    """Löscht Betriebsdaten des aktuellen Accounts."""
    denied = _require_admin()
    if denied:
        return denied
    confirm = (request.get_json(silent=True) or {}).get("confirm")
    if confirm != "ALLE DATEN LOESCHEN":
        return (
            jsonify(
                {
                    "error": 'Bestätigung erforderlich: confirm="ALLE DATEN LOESCHEN"',
                    "code": 400,
                }
            ),
            400,
        )
    s = g.settings
    langfuse_wipe: LangfuseWipeService | None = None
    if s.langfuse_secret_key and s.langfuse_public_key:
        langfuse_wipe = LangfuseWipeService(
            public_key=s.langfuse_public_key,
            secret_key=s.langfuse_secret_key,
            host=s.langfuse_host or None,
        )
    counts = DataWipeService(g.ctx.db, langfuse_wipe=langfuse_wipe).wipe_account(
        _account_id()
    )
    return jsonify(WipeDataResponse(deleted=counts).model_dump()), 200
