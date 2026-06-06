"""Admin-Diagnose: Mail/WhatsApp pro Mandant."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from backend.infrastructure.adapters.mail.connector import MailTestResult
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRecord,
)
from tests.web.test_registration import _register_payload


def _approve_tenant(client: Any, auth_headers: dict[str, str], email: str) -> str:
    client.post("/api/auth/register", json=_register_payload(email=email))
    pending = client.get("/api/admin/accounts?status=pending", headers=auth_headers)
    tenant = next(i for i in pending.get_json()["items"] if i["contact_email"] == email)
    client.post(
        f"/api/admin/accounts/{tenant['id']}/approve",
        headers=auth_headers,
    )
    return str(tenant["id"])


def test_admin_mail_connection_read_only(
    client: Any,
    auth_headers: dict[str, str],
    app: Any,
) -> None:
    """GET mail/connection liefert Status ohne Passwort."""
    account_id = _approve_tenant(client, auth_headers, "diag-mail@test.local")
    ctx = app.extensions["ctx"]
    record = ctx.mail_connection_repo.get_or_create(account_id)
    record.email_address = "tenant@example.com"
    record.imap_password = "secret"
    ctx.mail_connection_repo.save(record)

    resp = client.get(
        f"/api/admin/accounts/{account_id}/mail/connection",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["email_address"] == "tenant@example.com"
    assert data["imap_password_set"] is True
    assert "secret" not in str(data)


def test_admin_mail_test_uses_tenant_config(
    client: Any,
    auth_headers: dict[str, str],
) -> None:
    """POST mail/test nutzt Mandanten-Verbindung."""
    account_id = _approve_tenant(client, auth_headers, "diag-mail-test@test.local")
    with patch(
        "backend.api.services.admin_diagnostics_service.MailConnectionService.test_connection",
        return_value=MailTestResult(success=True, message="OK", mailbox_count=3),
    ) as mock_test:
        resp = client.post(
            f"/api/admin/accounts/{account_id}/mail/test",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
    mock_test.assert_called_once_with(account_id)


def test_admin_whatsapp_info_lists_all_templates(
    client: Any,
    auth_headers: dict[str, str],
) -> None:
    """GET whatsapp liefert alle vier Template-Slots."""
    account_id = _approve_tenant(client, auth_headers, "diag-wa-info@test.local")
    resp = client.get(
        f"/api/admin/accounts/{account_id}/whatsapp",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    templates = resp.get_json()["templates"]
    assert set(templates.keys()) == {
        "cleaning_task",
        "status_notice",
        "guest_inquiry",
        "support_ticket",
    }


def test_admin_update_whatsapp_templates(
    client: Any,
    auth_headers: dict[str, str],
) -> None:
    """PUT whatsapp/templates speichert Mandanten-Template-Namen."""
    account_id = _approve_tenant(client, auth_headers, "diag-wa-tpl@test.local")
    resp = client.put(
        f"/api/admin/accounts/{account_id}/whatsapp/templates",
        headers=auth_headers,
        json={
            "template_cleaning_task": "custom_cleaning_de",
            "template_status_notice": "custom_status_de",
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["templates"]["cleaning_task"] == "custom_cleaning_de"
    assert data["templates"]["status_notice"] == "custom_status_de"


def test_admin_whatsapp_test_hello_world(
    client: Any,
    auth_headers: dict[str, str],
    app: Any,
) -> None:
    """WhatsApp hello_world Test für Mandant."""
    account_id = _approve_tenant(client, auth_headers, "diag-wa@test.local")
    ctx = app.extensions["ctx"]
    ctx.platform_settings_repo.save(
        PlatformSettingsRecord(
            id=account_id,
            whatsapp_access_token="token",
            whatsapp_phone_number_id="123456789012345",
            whatsapp_test_recipient="+491701234567",
        )
    )
    with patch(
        "backend.api.services.admin_diagnostics_service.send_whatsapp_admin_test",
    ) as mock_send:
        from backend.core.models.notification import WhatsAppSendResult

        mock_send.return_value = WhatsAppSendResult(
            success=True,
            provider_message_id="wamid.test",
        )
        resp = client.post(
            f"/api/admin/accounts/{account_id}/whatsapp/test",
            headers=auth_headers,
            json={"template": "hello_world"},
        )
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
    mock_send.assert_called_once()


def test_admin_diagnostics_forbidden_for_tenant(
    client: Any,
    auth_headers: dict[str, str],
    tenant_owner_auth_headers: dict[str, str],
) -> None:
    """Mandanten dürfen Admin-Diagnose nicht aufrufen."""
    account_id = _approve_tenant(client, auth_headers, "diag-forbidden@test.local")
    resp = client.get(
        f"/api/admin/accounts/{account_id}/mail/connection",
        headers=tenant_owner_auth_headers,
    )
    assert resp.status_code == 403


def test_admin_diagnostics_unknown_account(
    client: Any,
    auth_headers: dict[str, str],
) -> None:
    """Unbekannte account_id → 404."""
    resp = client.get(
        "/api/admin/accounts/unknown-id/mail/connection",
        headers=auth_headers,
    )
    assert resp.status_code == 404
