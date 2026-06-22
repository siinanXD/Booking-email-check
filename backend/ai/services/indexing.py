"""Asynchrone Indexierung (Hintergrund, entkoppelt vom Antwortpfad)."""

from __future__ import annotations

import asyncio
import logging
import threading
from functools import lru_cache
from typing import Any, Protocol

from langfuse.decorators import langfuse_context, observe

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.services.semantic_chunking import semantic_chunk
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
        *,
        max_chunk_tokens: int = 512,
        overlap_tokens: int = 64,
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._repo = embedding_repo
        self._chunk_repo = chunk_repo
        self._embed = embed_client
        self._alerts = alerts
        self._max_chunk_tokens = max_chunk_tokens
        self._overlap_tokens = overlap_tokens
        self._embedding_model = embedding_model

    def schedule_index(
        self,
        correlation_id: str,
        body: str,
        extraction: BookingExtraction | None = None,
        *,
        account_id: str | None = None,
        subject: str | None = None,
        body_html: str | None = None,
    ) -> None:
        """Startet Indexierung ohne den Aufrufer zu blockieren."""

        def _coro() -> Any:
            return self._index_async(
                correlation_id,
                body,
                extraction,
                account_id,
                subject=subject,
                body_html=body_html,
            )

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_coro(), name=f"index-{correlation_id}")
        except RuntimeError:
            threading.Thread(
                target=asyncio.run,
                args=(_coro(),),
                daemon=True,
                name=f"index-{correlation_id}",
            ).start()

    def purge(self, correlation_id: str, *, account_id: str | None = None) -> int:
        """Entfernt alle Chunks/Embeddings einer Mail (Nicht-Buchungs-Cleanup).

        Hält den Vektor-Index frei von irrelevanten Mails (z. B. Marketing,
        intent=other), die als Stilreferenz nur Rauschen wären.
        """
        deleted = self._repo.delete_by_correlation_id(
            correlation_id, account_id=account_id
        )
        if self._chunk_repo is not None:
            self._chunk_repo.delete_by_correlation_id(
                correlation_id, account_id=account_id
            )
        return deleted

    async def _index_async(
        self,
        correlation_id: str,
        body: str,
        extraction: BookingExtraction | None,
        account_id: str | None = None,
        *,
        subject: str | None = None,
        body_html: str | None = None,
    ) -> None:
        try:
            intent = (
                extraction.intent.value if extraction and extraction.intent else None
            )
            chunks = semantic_chunk(
                body,
                subject=subject,
                extraction=extraction,
                body_html=body_html,
                max_tokens=self._max_chunk_tokens,
                overlap_tokens=self._overlap_tokens,
                embedding_model=self._embedding_model,
            )
            # Erst alle Embeddings berechnen, dann ersetzen: Schlägt das Embedding
            # fehl, bleiben die alten Chunks erhalten (kein Datenverlust).
            embedded = [
                (chunk, await asyncio.to_thread(self._embed.embed, chunk.text))
                for chunk in chunks
            ]
            # Idempotenz: alte Chunks/Embeddings vor Re-Index entfernen, damit bei
            # weniger Chunks keine Waisen zurückbleiben.
            await asyncio.to_thread(
                self._repo.delete_by_correlation_id,
                correlation_id,
                account_id=account_id,
            )
            if self._chunk_repo is not None:
                await asyncio.to_thread(
                    self._chunk_repo.delete_by_correlation_id,
                    correlation_id,
                    account_id=account_id,
                )
            for chunk, vector in embedded:
                chunk_id = f"{correlation_id}:{chunk.chunk_index}"
                if self._chunk_repo is not None:
                    await asyncio.to_thread(
                        self._chunk_repo.upsert_chunk,
                        chunk_id,
                        correlation_id,
                        chunk.text,
                        intent,
                        account_id=account_id,
                        chunk_index=chunk.chunk_index,
                        token_count=chunk.token_count,
                        char_start=chunk.char_start,
                        char_end=chunk.char_end,
                        context_prefix=chunk.context_prefix,
                    )
                await asyncio.to_thread(
                    self._repo.upsert_chunk,
                    chunk_id,
                    correlation_id,
                    chunk.text,
                    vector,
                    intent,
                    account_id=account_id,
                    chunk_index=chunk.chunk_index,
                    token_count=chunk.token_count,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    context_prefix=chunk.context_prefix,
                )
        except Exception as exc:
            logger.exception("Async indexing failed for %s", correlation_id)
            if self._alerts is not None:
                self._alerts.check_extraction_failure(
                    correlation_id,
                    f"indexing: {exc}",
                )
