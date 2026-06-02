"""Asynchrone Indexierung (Hintergrund, entkoppelt vom Antwortpfad)."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Protocol

from langfuse.decorators import langfuse_context, observe

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.infrastructure.repositories.embedding_repository import EmbeddingRepository

logger = logging.getLogger(__name__)


class EmbeddingFn(Protocol):
    """OpenAI- oder Mock-Embeddings."""

    def embed(self, text: str) -> list[float]:
        """Return an embedding vector for the supplied text."""
        ...


def chunk_text(body: str, max_chunks: int = 3) -> list[str]:
    """Schlankes Chunking: Absätze oder ein Ganzes."""
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    if not paragraphs:
        return [body] if body.strip() else []
    if len(paragraphs) <= max_chunks:
        return paragraphs
    return paragraphs[:max_chunks]


class EmbeddingClient:
    """OpenAI Embeddings client."""

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        use_langfuse: bool = False,
        tracing: bool = False,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._tracing = tracing
        if use_langfuse:
            from langfuse.openai import OpenAI
        else:
            from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model

    @observe(
        name="embed",
        as_type="generation",
        capture_input=False,
        capture_output=False,
    )  # type: ignore[misc]
    def embed(self, text: str) -> list[float]:
        """Execute the operation."""
        if self._tracing:
            langfuse_context.update_current_observation(model=self._model)
        response = self._client.embeddings.create(
            input=text,
            model=self._model,
        )
        return list(response.data[0].embedding)


class IndexingService:
    """Indexiert Mail-Text nach Extraktion im Hintergrund."""

    def __init__(
        self,
        embedding_repo: EmbeddingRepository,
        embed_client: EmbeddingFn,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._repo = embedding_repo
        self._embed = embed_client

    def schedule_index(
        self,
        correlation_id: str,
        body: str,
        extraction: BookingExtraction | None = None,
    ) -> None:
        """Startet Indexierung ohne den Aufrufer zu blockieren."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                self._index_async(correlation_id, body, extraction),
                name=f"index-{correlation_id}",
            )
        except RuntimeError:
            threading.Thread(
                target=asyncio.run,
                args=(self._index_async(correlation_id, body, extraction),),
                daemon=True,
                name=f"index-{correlation_id}",
            ).start()

    async def _index_async(
        self,
        correlation_id: str,
        body: str,
        extraction: BookingExtraction | None,
    ) -> None:
        intent = extraction.intent.value if extraction and extraction.intent else None
        chunks = chunk_text(body)
        for i, chunk in enumerate(chunks):
            vector = await asyncio.to_thread(self._embed.embed, chunk)
            chunk_id = f"{correlation_id}:{i}"
            await asyncio.to_thread(
                self._repo.upsert_chunk,
                chunk_id,
                correlation_id,
                chunk,
                vector,
                intent,
            )
