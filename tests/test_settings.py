"""Tests für zentrale Settings-Validierung."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.core.config.settings import Settings


def _base_env(**overrides: object) -> dict[str, object]:
    env: dict[str, object] = {
        "OPENAI_API_KEY": "test",
        "MONGODB_URI": "mongodb://localhost:27017",
        "LANGFUSE_PUBLIC_KEY": "pk",
        "LANGFUSE_SECRET_KEY": "sk",
    }
    env.update(overrides)
    return env


@pytest.mark.parametrize(
    "uri",
    [
        "mongodb://localhost:27017",
        "mongodb+srv://cluster.example.net",
    ],
)
def test_mongodb_uri_valid(uri: str) -> None:
    """Gültige MongoDB-URIs werden akzeptiert."""
    settings = Settings.model_validate(_base_env(MONGODB_URI=uri))
    assert settings.mongodb_uri == uri


@pytest.mark.parametrize(
    "uri",
    [
        "postgres://localhost/db",
        "",
    ],
)
def test_mongodb_uri_invalid(uri: str) -> None:
    """Ungültige MongoDB-URIs werden abgelehnt."""
    with pytest.raises(ValidationError):
        Settings.model_validate(_base_env(MONGODB_URI=uri))
