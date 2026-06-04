"""Tests für Postfach-API."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.infrastructure.adapters.mail.connector import MailTestResult


@pytest.fixture
def member_auth_headers(
    client: object, web_settings: object, tenant_account_id: str
) -> dict[str, str]:
    """JWT für Account-Mitglied ohne Admin-Rechte."""
    from werkzeug.security import generate_password_hash

    app = client.application  # type: ignore[union-attr]
    ctx = app.extensions["ctx"]
    ctx.user_repo.create(
        email="member@test.local",
        password_hash=generate_password_hash("member-pass"),
        role="member",
        account_id=tenant_account_id,
    )
    resp = client.post(  # type: ignore[union-attr]
        "/api/auth/login",
        json={"email": "member@test.local", "password": "member-pass"},
    )
    assert resp.status_code == 200
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_mail_connection_creates_default(
    client: object, auth_headers: dict[str, str]
) -> None:
    resp = client.get("/api/mail/connection", headers=auth_headers)  # type: ignore[union-attr]
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["provider"] == "imap"
    assert data["onboarding_completed"] is False
    assert len(data["imap_presets"]) >= 1


def test_update_mail_connection_imap(
    client: object, auth_headers: dict[str, str]
) -> None:
    resp = client.put(  # type: ignore[union-attr]
        "/api/mail/connection",
        headers=auth_headers,
        json={
            "provider": "imap",
            "email_address": "vermieter@gmx.de",
            "preset": "gmx",
            "imap_username": "vermieter@gmx.de",
            "imap_password": "secret-app-pass",
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["email_address"] == "vermieter@gmx.de"
    assert data["imap_host"] == "imap.gmx.net"
    assert data["imap_password_set"] is True


def test_mail_connection_forbidden_for_member(
    client: object, member_auth_headers: dict[str, str]
) -> None:
    resp = client.get("/api/mail/connection", headers=member_auth_headers)  # type: ignore[union-attr]
    assert resp.status_code == 403


def test_mail_test_connection(client: object, auth_headers: dict[str, str]) -> None:
    client.put(  # type: ignore[union-attr]
        "/api/mail/connection",
        headers=auth_headers,
        json={
            "provider": "imap",
            "email_address": "test@gmx.de",
            "preset": "gmx",
            "imap_username": "test@gmx.de",
            "imap_password": "pw",
        },
    )
    with patch(
        "backend.features.mail.mail_connection_service.build_mail_connector"
    ) as mock_build:
        connector = MagicMock()
        connector.test_connection.return_value = MailTestResult(
            success=True,
            message="OK",
            mailbox_count=42,
        )
        mock_build.return_value = connector
        resp = client.post("/api/mail/test", headers=auth_headers)  # type: ignore[union-attr]
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["mailbox_count"] == 42


def test_mail_sync_requires_pollable_connection(
    client: object, auth_headers: dict[str, str]
) -> None:
    resp = client.post("/api/mail/sync", headers=auth_headers)  # type: ignore[union-attr]
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False


def test_mail_sync_runs_poll(
    client: object, auth_headers: dict[str, str], tenant_account_id: str
) -> None:
    client.put(  # type: ignore[union-attr]
        "/api/mail/connection",
        headers=auth_headers,
        json={
            "provider": "outlook",
            "outlook_auth_mode": "oauth",
            "onboarding_completed": True,
        },
    )
    app = client.application  # type: ignore[union-attr]
    ctx = app.extensions["ctx"]
    record = ctx.mail_connection_repo.get_or_create(tenant_account_id)
    record.outlook_token_cache = '{"AccessToken": {"secret": "x"}}'
    ctx.mail_connection_repo.save(record)

    with (
        patch(
            "backend.api.blueprints.mail.build_mail_poll_service_from_context"
        ) as mock_build,
        patch(
            "backend.api.blueprints.mail.build_mail_reprocess_service"
        ) as mock_reprocess_build,
    ):
        poll = MagicMock()
        from backend.features.mail.mail_poll_service import (
            AccountPollSummary,
            MailPollBatchResult,
        )

        poll.run_all.return_value = MailPollBatchResult(
            accounts_polled=1,
            total_processed=2,
            summaries=[
                AccountPollSummary(
                    account_id=tenant_account_id,
                    provider="outlook",
                    processed=2,
                    duplicates=1,
                    item_errors=["workflow failed: m1"],
                )
            ],
        )
        mock_build.return_value = poll
        resp = client.post("/api/mail/sync", headers=auth_headers)  # type: ignore[union-attr]

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is False
    assert data["processed"] == 2
    assert data["duplicates"] == 1
    assert data["error_count"] == 1
    assert data["item_errors"] == ["workflow failed: m1"]
    assert data["reprocessed"] == 0
    poll.run_all.assert_called_once_with(account_ids=[tenant_account_id])
    mock_reprocess_build.assert_not_called()


def test_mail_sync_reprocess_when_requested(
    client: object, auth_headers: dict[str, str], tenant_account_id: str
) -> None:
    client.put(  # type: ignore[union-attr]
        "/api/mail/connection",
        headers=auth_headers,
        json={
            "provider": "outlook",
            "outlook_auth_mode": "oauth",
            "onboarding_completed": True,
        },
    )
    app = client.application  # type: ignore[union-attr]
    ctx = app.extensions["ctx"]
    record = ctx.mail_connection_repo.get_or_create(tenant_account_id)
    record.outlook_token_cache = '{"AccessToken": {"secret": "x"}}'
    ctx.mail_connection_repo.save(record)

    with (
        patch(
            "backend.api.blueprints.mail.build_mail_poll_service_from_context"
        ) as mock_build,
        patch(
            "backend.api.blueprints.mail.build_mail_reprocess_service"
        ) as mock_reprocess_build,
    ):
        poll = MagicMock()
        from backend.features.mail.mail_poll_service import (
            AccountPollSummary,
            MailPollBatchResult,
        )
        from backend.features.mail.mail_reprocess_service import MailReprocessResult

        poll.run_all.return_value = MailPollBatchResult(
            accounts_polled=1,
            total_processed=0,
            summaries=[
                AccountPollSummary(
                    account_id=tenant_account_id,
                    provider="outlook",
                    processed=0,
                    duplicates=0,
                )
            ],
        )
        reprocess = MagicMock()
        reprocess.reprocess_stuck_bookings.return_value = MailReprocessResult(
            completed=1,
            errors=["corr-x: timeout"],
        )
        mock_build.return_value = poll
        mock_reprocess_build.return_value = reprocess
        resp = client.post(  # type: ignore[union-attr]
            "/api/mail/sync?reprocess=true",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["reprocessed"] == 1
    assert data["reprocess_errors"] == ["corr-x: timeout"]
    reprocess.reprocess_stuck_bookings.assert_called_once_with(
        tenant_account_id,
        limit=25,
    )


def test_auth_me_includes_mail_onboarding(
    client: object, tenant_owner_auth_headers: dict[str, str]
) -> None:
    client.get("/api/mail/connection", headers=tenant_owner_auth_headers)  # type: ignore[union-attr]
    resp = client.get("/api/auth/me", headers=tenant_owner_auth_headers)  # type: ignore[union-attr]
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["mail_onboarding_completed"] is False
    assert data["mail_connection_status"] == "disconnected"

    client.put(  # type: ignore[union-attr]
        "/api/mail/connection",
        headers=tenant_owner_auth_headers,
        json={"onboarding_completed": True},
    )
    resp = client.get("/api/auth/me", headers=tenant_owner_auth_headers)  # type: ignore[union-attr]
    assert resp.get_json()["mail_onboarding_completed"] is True
