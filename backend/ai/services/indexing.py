"""Asynchrone Indexierung (Hintergrund, entkoppelt vom Antwortpfad)."""

from __future__ import annotations

import asyncio
import logging
import threading
from functools import lru_cache
from typing import Any, Protocol

from langfuse.decorators import langfuse_context, observe

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.infrastructure.observability.alerts import AlertService
from backend.infrastructure.repositories.chunk_repository import ChunkRepository
from backend.infrastructure.repositories.embedding_repository import EmbeddingRepository

logger = logging.getLogger(__name__)

# text-embedding-3-* akzeptieren max. 8192 Tokens pro Input. Mit Sicherheitsmarge.
_MAX_EMBED_TOKENS = 8000
# Fallback ohne tiktoken: grobe Schätzung ~4 Zeichen je Token.
_CHARS_PER_TOKEN = 4


@lru_cache(maxsize=1)
def _encoder() -> Any:  # noqa: ANN401 - tiktoken.Encoding, lazy importiert
    """Gecachter tiktoken-Encoder (cl100k_base passt zu text-embedding-3-*)."""
    import tiktoken

    return tiktoken.get_encoding("cl100k_base")


def truncate_for_embedding(text: str, max_tokens: int = _MAX_EMBED_TOKENS) -> str:
    """Kürzt Text aufs Token-Limit des Embedding-Modells.

    Nutzt tiktoken; fällt bei jedem Fehler auf eine zeichenbasierte Schätzung
    zurück, damit das Embedding nie an OpenAIs 8192-Token-Grenze scheitert.
    """
    try:
        encoder = _encoder()
        tokens = encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text
        truncated = str(encoder.decode(tokens[:max_tokens]))
        logger.warning(
            "Embedding-Input gekürzt: %d → %d Tokens", len(tokens), max_tokens
        )
        return truncated
    except Exception:  # noqa: BLE001 - tiktoken-Fehler dürfen Indexierung nicht stoppen
        max_chars = max_tokens * _CHARS_PER_TOKEN
        if len(text) <= max_chars:
            return text
        logger.warning(
            "Embedding-Input zeichenbasiert gekürzt: %d → %d Zeichen "
            "(tiktoken nicht verfügbar)",
            len(text),
            max_chars,
        )
        return text[:max_chars]


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
            input=truncate_for_embedding(text),
            model=self._model,
        )
        return list(response.data[0].embedding)


class IndexingService:
    """Indexiert Mail-Text nach Extraktion im Hintergrund."""

    def __init__(
        self,
        embedding_repo: EmbeddingRepository,
        embed_client: EmbeddingFn,
        chunk_repo: ChunkRepository | None = None,
        alerts: AlertService | None = None,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._repo = embedding_repo
        self._chunk_repo = chunk_repo
        self._embed = embed_client
        self._alerts = alerts

    def schedule_index(
        self,
        correlation_id: str,
        body: str,
        extraction: BookingExtraction | None = None,
        *,
        account_id: str | None = None,
    ) -> None:
        """Startet Indexierung ohne den Aufrufer zu blockieren."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                self._index_async(correlation_id, body, extraction, account_id),
                name=f"index-{correlation_id}",
            )
        except RuntimeError:
            threading.Thread(
                target=asyncio.run,
                args=(self._index_async(correlation_id, body, extraction, account_id),),
                daemon=True,
                name=f"index-{correlation_id}",
            ).start()

    async def _index_async(
        self,
        correlation_id: str,
        body: str,
        extraction: BookingExtraction | None,
        account_id: str | None = None,
    ) -> None:
        try:
            intent = (
                extraction.intent.value if extraction and extraction.intent else None
            )
            chunks = chunk_text(body)
            for i, chunk in enumerate(chunks):
                vector = await asyncio.to_thread(self._embed.embed, chunk)
                chunk_id = f"{correlation_id}:{i}"
                if self._chunk_repo is not None:
                    await asyncio.to_thread(
                        self._chunk_repo.upsert_chunk,
                        chunk_id,
                        correlation_id,
                        chunk,
                        intent,
                        account_id=account_id,
                    )
                await asyncio.to_thread(
                    self._repo.upsert_chunk,
                    chunk_id,
                    correlation_id,
                    chunk,
                    vector,
                    intent,
                    account_id=account_id,
                )
        except Exception as exc:
            logger.exception("Async indexing failed for %s", correlation_id)
            if self._alerts is not None:
                self._alerts.check_extraction_failure(
                    correlation_id,
                    f"indexing: {exc}",
                )
