"""Integrationstests (live MongoDB, optional)."""

from __future__ import annotations

import os

import pytest

from config.settings import Settings
from repositories.mongo import ping


@pytest.mark.integration
def test_mongo_ping() -> None:
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        pytest.skip("MONGODB_URI not set")
    settings = Settings.model_validate(
        {
            "OPENAI_API_KEY": "sk-test",
            "MONGODB_URI": uri,
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test",
        }
    )
    assert ping(settings) is True
