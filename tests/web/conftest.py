"""Fixtures für Flask-Web-Tests."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from werkzeug.security import generate_password_hash

from config.settings import Settings
from web.app import create_app
from web.auth.token_blocklist import clear_for_tests


def _test_settings() -> Settings:
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
        }
    )


@pytest.fixture
def web_settings() -> Settings:
    """Settings für Web-Tests."""
    return _test_settings()


@pytest.fixture
def app(mock_db: object, web_settings: Settings) -> Generator:
    """Flask-App mit mongomock (via patch)."""
    clear_for_tests()
    from unittest.mock import patch

    settings = web_settings
    with patch("config.factory.get_database", return_value=mock_db):
        with patch("workflows.checkpointer.build_checkpointer") as mock_cp:
            from langgraph.checkpoint.memory import MemorySaver

            mock_cp.return_value = MemorySaver()
            flask_app = create_app(settings)
            ctx = flask_app.extensions["ctx"]
            ctx.user_repo.ensure_admin(
                settings.admin_email,
                generate_password_hash(settings.admin_password),
            )
            flask_app.config["TESTING"] = True
            yield flask_app


@pytest.fixture
def client(app: object) -> object:
    """Flask test client."""
    return app.test_client()  # type: ignore[union-attr]


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
