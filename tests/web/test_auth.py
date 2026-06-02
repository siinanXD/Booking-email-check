"""Auth-API-Tests."""

from __future__ import annotations

from typing import Any


def test_login_success(client: Any, web_settings: Any) -> None:
    """Gültige Credentials liefern JWT."""
    resp = client.post(
        "/api/auth/login",
        json={
            "email": web_settings.admin_email,
            "password": web_settings.admin_password,
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_invalid_password(client: Any, web_settings: Any) -> None:
    """Falsches Passwort → 401."""
    resp = client.post(
        "/api/auth/login",
        json={"email": web_settings.admin_email, "password": "wrong"},
    )
    assert resp.status_code == 401


def test_me_requires_auth(client: Any) -> None:
    """Ohne Token → 401."""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_health(client: Any) -> None:
    """Health ohne Auth."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_me_with_token(client: Any, auth_headers: dict[str, str]) -> None:
    """Mit Token → Profil."""
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["email"] == "admin@test.local"
