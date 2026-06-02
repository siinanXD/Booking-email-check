"""Asynchrone Indexierung (Hintergrund, entkoppelt vom Antwortpfad)."""

from __future__ import annotations

import asyncio

from repositories.embedding_repository import EmbeddingRepository
from schemas.booking.extraction import BookingExtraction


def chunk_text(body: str, max_chunks: int = 3) -> list[str]:
    """Schlankes Chunking: Absätze oder ein Ganzes."""
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    if not paragraphs:
        return [body] if body.strip() else []
    if len(paragraphs) <= max_chunks:
        return paragraphs
    return paragraphs[:max_chunks]


class EmbeddingClient:
    """OpenAI Embeddings."""

    def __init__(self, api_key: str, model: str) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def embed(self, text: str) -> list[float]:
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
        embed_client: EmbeddingClient,
    ) -> None:
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
            asyncio.run(self._index_async(correlation_id, body, extraction))

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
