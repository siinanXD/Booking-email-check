"""Semantisches Chunking für Mail-Indexierung (Token-Limit, Overlap, Kontext-Prefix)."""

from __future__ import annotations

from dataclasses import dataclass

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.services._chunk_packer import (
    MIN_CHUNK_TOKENS,
    _pack_body_chunks,
    _split_segments,
)
from backend.ai.services._chunk_packer import (
    count_tokens as count_tokens,
)
from backend.core.utils.text import normalize_body


@dataclass(frozen=True)
class SemanticChunk:
    """Ein indexierbares Textsegment inkl. Metadaten."""

    chunk_index: int
    text: str
    body_text: str
    context_prefix: str
    token_count: int
    char_start: int
    char_end: int


def build_context_prefix(
    *,
    subject: str | None = None,
    intent: str | None = None,
    property_name: str | None = None,
    booking_number: str | None = None,
) -> str:
    """Kompakter Kontext-Prefix pro Chunk (Roadmap Phase 12)."""
    parts: list[str] = []
    if subject and subject.strip():
        parts.append(subject.strip())
    if intent:
        parts.append(intent)
    if property_name and property_name.strip():
        parts.append(property_name.strip())
    if booking_number and booking_number.strip():
        parts.append(booking_number.strip())
    if not parts:
        return ""
    return " | ".join(parts) + "\n\n"


def preprocess_mail_body(body: str, body_html: str | None = None) -> str:
    """Zitat-Strip, HTML-/CSS-Bereinigung, Entity-Dekodierung, Whitespace.

    Marketing-Mails schleppen oft ``<style>``-Blöcke (``@font-face { … }``) und
    HTML-Entities (``&nbsp;``, ``&zwnj;``) in den Plaintext — die verschlechtern
    Embeddings. Sie werden hier entfernt/dekodiert.
    """
    import html
    import re

    text = normalize_body(body, body_html)
    text = re.sub(r"(?is)<(style|script)\b.*?</\1>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def semantic_chunk(
    body: str,
    *,
    subject: str | None = None,
    extraction: BookingExtraction | None = None,
    body_html: str | None = None,
    max_tokens: int = 512,
    overlap_tokens: int = 64,
    embedding_model: str = "text-embedding-3-small",
    min_chunk_tokens: int = MIN_CHUNK_TOKENS,
) -> list[SemanticChunk]:
    """Erzeugt semantische Chunks mit Kontext-Prefix für die Indexierung."""
    normalized = preprocess_mail_body(body, body_html)
    if not normalized:
        return []

    intent = extraction.intent.value if extraction and extraction.intent else None
    context_prefix = build_context_prefix(
        subject=subject,
        intent=intent,
        property_name=extraction.property_name if extraction else None,
        booking_number=extraction.booking_number if extraction else None,
    )
    prefix_tokens = count_tokens(context_prefix, embedding_model=embedding_model)
    max_body_tokens = max(1, max_tokens - prefix_tokens)

    segments = _split_segments(
        normalized,
        embedding_model=embedding_model,
        max_segment_tokens=max_body_tokens,
        overlap_tokens=overlap_tokens,
    )
    if not segments:
        return []

    total_body_tokens = sum(seg.token_count for seg in segments)
    if total_body_tokens <= max_body_tokens:
        return [
            SemanticChunk(
                chunk_index=0,
                text=f"{context_prefix}{normalized}".strip(),
                body_text=normalized,
                context_prefix=context_prefix,
                token_count=prefix_tokens + total_body_tokens,
                char_start=0,
                char_end=len(normalized),
            )
        ]

    body_chunks = _pack_body_chunks(
        normalized,
        segments,
        max_body_tokens=max_body_tokens,
        overlap_tokens=overlap_tokens,
        min_chunk_tokens=min_chunk_tokens,
    )
    return [
        SemanticChunk(
            chunk_index=i,
            text=f"{context_prefix}{chunk_body}".strip(),
            body_text=chunk_body,
            context_prefix=context_prefix,
            token_count=prefix_tokens
            + count_tokens(chunk_body, embedding_model=embedding_model),
            char_start=char_start,
            char_end=char_end,
        )
        for i, (chunk_body, char_start, char_end) in enumerate(body_chunks)
    ]
