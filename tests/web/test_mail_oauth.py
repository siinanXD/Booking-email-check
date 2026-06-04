"""Outlook OAuth API tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


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


def test_outlook_authorize_url_requires_admin(
    client: object, member_auth_headers: dict[str, str]
) -> None:
    resp = client.get(  # type: ignore[union-attr]
        "/api/mail/outlook/authorize-url",
        headers=member_auth_headers,
    )
    assert resp.status_code == 403


def test_outlook_authorize_url_error(
    client: object, auth_headers: dict[str, str]
) -> None:
    mock_service = MagicMock()
    mock_service.build_authorize_url.side_effect = ValueError(
        "AZURE_CLIENT_ID ist nicht konfiguriert"
    )
    with patch(
        "backend.api.blueprints.mail._oauth_service",
        return_value=mock_service,
    ):
        resp = client.get(  # type: ignore[union-attr]
            "/api/mail/outlook/authorize-url",
            headers=auth_headers,
        )
    assert resp.status_code == 400


def test_outlook_authorize_url_success(
    client: object, auth_headers: dict[str, str]
) -> None:
    mock_service = MagicMock()
    mock_service.build_authorize_url.return_value = (
        "https://login.microsoftonline.com/authorize"
    )
    with patch(
        "backend.api.blueprints.mail._oauth_service",
        return_value=mock_service,
    ):
        resp = client.get(  # type: ignore[union-attr]
            "/api/mail/outlook/authorize-url",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.get_json()["authorize_url"].startswith("https://")


def test_outlook_oauth_callback_invalid_state(client: object) -> None:
    resp = client.get("/api/mail/outlook/callback?state=unknown")  # type: ignore[union-attr]
    assert resp.status_code == 302
    assert "outlook=error" in resp.headers.get("Location", "")


def test_msal_oauth_callback_alias(client: object) -> None:
    resp = client.get("/api/msal/callback?state=unknown")  # type: ignore[union-attr]
    assert resp.status_code == 302
    assert "outlook=error" in resp.headers.get("Location", "")
