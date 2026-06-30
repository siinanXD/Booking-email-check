"""Auswahl von LLM- und Embedding-Client anhand der Settings (live/mock)."""

from __future__ import annotations

from backend.ai.services.classification import LLMClient
from backend.ai.services.indexing import EmbeddingClient, EmbeddingFn
from backend.ai.services.openai_client import OpenAIClient
from backend.core.config.settings import Settings


def build_llm_and_embeddings(
    cfg: Settings,
    *,
    tracing: bool,
) -> tuple[LLMClient, EmbeddingFn]:
    """Erzeugt LLM- und Embedding-Client je nach ``LLM_MODE``."""
    llm_mode = cfg.llm_mode.strip().lower()
    if llm_mode == "mock":
        from backend.ai.testing.mock_llm import MockEmbeddingClient, MockLLM

        return MockLLM(), MockEmbeddingClient()
    if llm_mode == "live":
        llm = OpenAIClient(cfg.openai_api_key, use_langfuse=False)
        embed_client = EmbeddingClient(
            cfg.openai_api_key,
            cfg.embedding_model,
            use_langfuse=False,
            tracing=tracing,
        )
        return llm, embed_client
    msg = f"Unsupported LLM_MODE: {cfg.llm_mode!r} (use live or mock)"
    raise ValueError(msg)
