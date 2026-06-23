"""Tests für Token-Usage-Logging an Langfuse-Generations."""

from __future__ import annotations

from unittest.mock import patch

from backend.infrastructure.observability import langfuse_client


def test_log_token_usage_sets_usage_details() -> None:
    """Prompt-/Completion-Tokens landen als usage_details (input/output/total)."""
    with patch.object(langfuse_client, "langfuse_context") as ctx:
        langfuse_client.log_token_usage(10, 5)
    ctx.update_current_observation.assert_called_once_with(
        usage_details={"input": 10, "output": 5, "total": 15}
    )


def test_log_token_usage_embedding_only_input() -> None:
    """Embeddings (kein Completion) ergeben total == input."""
    with patch.object(langfuse_client, "langfuse_context") as ctx:
        langfuse_client.log_token_usage(42)
    ctx.update_current_observation.assert_called_once_with(
        usage_details={"input": 42, "output": 0, "total": 42}
    )
