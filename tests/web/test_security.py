"""Sicherheitstests: Injection, CORS, Tenant-Isolation, Auth-Bypass, Rate Limiting."""

from __future__ import annotations

from typing import Any

import pytest

# ---------------------------------------------------------------------------
# MongoDB Injection
# ---------------------------------------------------------------------------


def test_login_rejects_operator_in_email(client: Any) -> None:
    """Pydantic-Validierung verhindert MongoDB-Operator als E-Mail-Wert."""
    resp = client.post(
        "/api/auth/login",
        json={"email": {"$gt": ""}, "password": "anything"},
    )
    # Pydantic expects a string → 422 Unprocessable Entity
    assert resp.status_code == 422


def test_login_rejects_operator_in_password(client: Any) -> None:
    """Operator als Passwort-Wert → 422, kein Datenleck."""
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@test.local", "password": {"$ne": None}},
    )
    assert resp.status_code == 422


def test_register_rejects_operator_injection(client: Any) -> None:
    """Operator-Wert im Registrierungsformular → 422."""
    resp = client.post(
        "/api/auth/register",
        json={
            "email": {"$gt": ""},
            "password": "longenough1",
            "password_confirm": "longenough1",
            "first_name": "Test",
            "last_name": "User",
            "phone": "+491701234567",
        },
    )
    assert resp.status_code in (400, 422)


def test_email_search_param_does_not_cause_server_error(
    client: Any, auth_headers: dict[str, str]
) -> None:
    """Regex-Sonderzeichen im search-Parameter → kein 500."""
    for value in (".*", "^admin", "[A-Z]+", "$or", r"\d+"):
        resp = client.get(
            f"/api/emails/?search={value}",
            headers=auth_headers,
        )
        assert resp.status_code in (200, 400), f"Unexpected status for search={value!r}"


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


def test_cors_allows_configured_origin(client: Any) -> None:
    """Konfigurierter CORS-Origin erhält Access-Control-Header."""
    resp = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert resp.status_code == 200
    assert "Access-Control-Allow-Origin" in resp.headers


def test_cors_preflight_allowed_origin(client: Any) -> None:
    """OPTIONS-Preflight von konfiguriertem Origin wird beantwortet."""
    resp = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.status_code in (200, 204)


def test_cors_blocks_unknown_origin(client: Any) -> None:
    """Unbekannter Origin erhält keinen Wildcard-Header."""
    resp = client.get(
        "/health",
        headers={"Origin": "https://evil.example.com"},
    )
    origin_header = resp.headers.get("Access-Control-Allow-Origin", "")
    assert origin_header != "*"
    assert "evil.example.com" not in origin_header


# ---------------------------------------------------------------------------
# Tenant Isolation
# ---------------------------------------------------------------------------


def test_tenant_cannot_access_other_tenants_email(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    mock_db: Any,
) -> None:
    """Tenant A kann Mails von Tenant B nicht abrufen."""
    from datetime import UTC, datetime

    from backend.core.models.email import ProcessingState, StoredEmail
    from backend.infrastructure.repositories.email_repository import EmailRepository

    other_account_id = "other-tenant-id-xyz"
    email_repo = EmailRepository(mock_db)
    email_repo.upsert_by_message_id(
        StoredEmail(
            message_id="m-other-tenant@test",
            from_address="guest@airbnb.com",
            subject="Private mail of other tenant",
            body_text="Secret booking content",
            received_at=datetime.now(UTC),
            correlation_id="corr-other-tenant",
            processing_state=ProcessingState.RECEIVED,
            account_id=other_account_id,
        )
    )

    # Tenant A tries to access Tenant B's email by correlation_id
    resp = client.get("/api/emails/corr-other-tenant", headers=auth_headers)
    assert resp.status_code == 404


def test_review_approve_blocked_for_other_tenant(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    mock_db: Any,
) -> None:
    """Approve auf fremde Correlation-ID → 404."""
    resp = client.post(
        "/api/review/approve",
        json={"correlation_id": "corr-belongs-to-nobody", "approved_body": "Hi"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Authentication Bypass
# ---------------------------------------------------------------------------


def test_protected_endpoint_requires_token(client: Any) -> None:
    """Ohne Authorization-Header → 401."""
    resp = client.get("/api/emails/")
    assert resp.status_code == 401


def test_tampered_token_rejected(client: Any) -> None:
    """Gefälschter Token → 401."""
    resp = client.get(
        "/api/emails/",
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.fake.payload"},
    )
    assert resp.status_code == 401


def test_malformed_authorization_header(client: Any) -> None:
    """Falsch formatierter Header → 401."""
    resp = client.get("/api/emails/", headers={"Authorization": "NotBearer abc"})
    assert resp.status_code == 401


def test_empty_bearer_token(client: Any) -> None:
    """Leerer Bearer-Token → 401."""
    resp = client.get("/api/emails/", headers={"Authorization": "Bearer "})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------


def test_response_includes_x_content_type_options(
    client: Any, auth_headers: dict[str, str]
) -> None:
    resp = client.get("/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"


def test_response_includes_x_frame_options(client: Any) -> None:
    resp = client.get("/health")
    assert resp.headers.get("X-Frame-Options") == "DENY"


def test_response_includes_referrer_policy(client: Any) -> None:
    resp = client.get("/health")
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_response_includes_correlation_id_header(client: Any) -> None:
    resp = client.get("/health")
    assert "X-Correlation-ID" in resp.headers
    assert len(resp.headers["X-Correlation-ID"]) == 36  # UUID length


def test_correlation_id_passthrough_from_request(client: Any) -> None:
    """X-Request-ID vom Client wird als Correlation-ID zurückgegeben."""
    custom_id = "my-custom-trace-id-12345678"
    resp = client.get("/health", headers={"X-Request-ID": custom_id})
    assert resp.headers.get("X-Correlation-ID") == custom_id


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_login_rate_limit_enforced(client: Any, web_settings: Any) -> None:
    """Mehr als 10 Login-Versuche pro Minute → 429."""
    # Exhaust the 10/minute limit with wrong credentials
    for _ in range(10):
        client.post(
            "/api/auth/login",
            json={"email": "nobody@test.local", "password": "wrong"},
        )
    resp = client.post(
        "/api/auth/login",
        json={"email": "nobody@test.local", "password": "wrong"},
    )
    assert resp.status_code == 429
