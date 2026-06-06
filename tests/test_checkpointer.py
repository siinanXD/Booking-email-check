"""Tests für LangGraph-Checkpointer-Konfiguration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.ai.workflows.checkpointer import build_checkpointer


def test_build_checkpointer_uses_memory_when_flag_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MemorySaver wenn WEB_USE_MEMORY_CHECKPOINTER gesetzt."""
    from backend.core.config.settings import Settings

    settings = Settings(
        OPENAI_API_KEY="sk-test",
        MONGODB_URI="mongodb://localhost:27017",
        LANGFUSE_PUBLIC_KEY="pk",
        LANGFUSE_SECRET_KEY="sk",
        WEB_USE_MEMORY_CHECKPOINTER="true",
    )
    cp = build_checkpointer(settings)
    assert type(cp).__name__ == "InMemorySaver" or type(cp).__name__ == "MemorySaver"


def test_build_checkpointer_uses_mongodb_saver_in_production() -> None:
    """MongoDBSaver wenn Paket installiert und Memory-Flag aus."""
    from backend.core.config.settings import Settings

    settings = Settings(
        OPENAI_API_KEY="sk-test",
        MONGODB_URI="mongodb://localhost:27017",
        LANGFUSE_PUBLIC_KEY="pk",
        LANGFUSE_SECRET_KEY="sk",
        WEB_USE_MEMORY_CHECKPOINTER="false",
        APP_ENV="production",
    )
    mock_saver = MagicMock()
    with patch(
        "langgraph.checkpoint.mongodb.MongoDBSaver",
        mock_saver,
        create=True,
    ):
        with patch(
            "backend.infrastructure.repositories.mongo.get_client",
            return_value=MagicMock(),
        ):
            cp = build_checkpointer(settings)
    assert cp is mock_saver.return_value
