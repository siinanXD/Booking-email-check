"""Fixtures für Flask-Web-Tests."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from werkzeug.security import generate_password_hash

from backend.api.app import create_app
from backend.api.auth.token_blocklist import (
    InMemoryBlocklistBackend,
    clear_for_tests,
    configure,
)
from backend.core.config.settings import Settings


def _test_settings() -> Settings:
    """Minimale Settings für Web-Tests."""
    return Settings.model_validate(
        {
            "OPENAI_API_KEY": "sk-test",
            "MONGODB_URI": "mongodb://localhost",
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test",
            "FLASK_SECRET_KEY": "x" * 32,
            "ADMIN_EMAIL": "admin@test.local",
            "ADMIN_PASSWORD": "test-password",
            "WEB_USE_MEMORY_CHECKPOINTER": "true",
            "LLM_MODE": "mock",
            # No background mail-poll thread in tests: otherwise create_app starts
            # a scheduler that fires a real poll after ~5 min and errors on the
            # missing AZURE_CLIENT_ID — a non-deterministic CI failure.
            "MAIL_POLL_IN_WEB": "false",
        }
    )


@pytest.fixture
def web_settings() -> Settings:
    """Settings für Web-Tests."""
    return _test_settings()


@pytest.fixture
def app(mock_db: object, web_settings: Settings) -> Generator:
    """Flask-App mit mongomock (via patch)."""
    configure(InMemoryBlocklistBackend())
    clear_for_tests()
    from unittest.mock import patch

    settings = web_settings
    with patch("backend.core.config.factory.get_database", return_value=mock_db):
        with patch("backend.ai.workflows.checkpointer.build_checkpointer") as mock_cp:
            from langgraph.checkpoint.memory import MemorySaver

            mock_cp.return_value = MemorySaver()
            flask_app = create_app(settings)
            ctx = flask_app.extensions["ctx"]
            account = ctx.account_repo.create(
                display_name="Test Admin",
                contact_email=settings.admin_email,
                account_type="business",
                company_name="Test Admin",
                status="active",
            )
            ctx.user_repo.ensure_platform_admin(
                settings.admin_email,
                generate_password_hash(settings.admin_password),
                account_id=account.id,
            )
            flask_app.config["TESTING"] = True
            yield flask_app


@pytest.fixture
def client(app: object) -> object:
    """Flask test client."""
    return app.test_client()  # type: ignore[union-attr]


@pytest.fixture
def tenant_account_id(client: object, auth_headers: dict[str, str]) -> str:
    """Account-ID des eingeloggten Test-Admins."""
    resp = client.get("/api/auth/me", headers=auth_headers)  # type: ignore[union-attr]
    assert resp.status_code == 200
    account_id = resp.get_json()["account_id"]
    assert isinstance(account_id, str)
    return account_id


@pytest.fixture
def tenant_owner_auth_headers(
    client: object, auth_headers: dict[str, str]
) -> dict[str, str]:
    """JWT für freigeschalteten Mandanten-Owner (Mail-Onboarding relevant)."""
    from tests.web.test_registration import _register_payload

    payload = _register_payload(email="owner-mail@test.local")
    client.post("/api/auth/register", json=payload)  # type: ignore[union-attr]
    pending = client.get(  # type: ignore[union-attr]
        "/api/admin/accounts?status=pending",
        headers=auth_headers,
    )
    tenant = next(
        i for i in pending.get_json()["items"] if i["contact_email"] == payload["email"]
    )
    client.post(  # type: ignore[union-attr]
        f"/api/admin/accounts/{tenant['id']}/approve",
        headers=auth_headers,
    )
    login = client.post(  # type: ignore[union-attr]
        "/api/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200
    token = login.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(client: object, web_settings: Settings) -> dict[str, str]:
    """JWT Authorization-Header."""
    resp = client.post(  # type: ignore[union-attr]
        "/api/auth/login",
        json={
            "email": web_settings.admin_email,
            "password": web_settings.admin_password,
        },
    )
    assert resp.status_code == 200
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
