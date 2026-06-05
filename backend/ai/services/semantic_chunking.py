"""Semantisches Chunking für Mail-Indexierung (Token-Limit, Overlap, Kontext-Prefix)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.core.utils.text import normalize_body

MIN_CHUNK_TOKENS = 32
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")


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


@lru_cache(maxsize=4)
def _encoding_for_model(model: str) -> Any:
    import tiktoken

    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, *, embedding_model: str = "text-embedding-3-small") -> int:
    """Zählt Tokens für das konfigurierte Embedding-Modell."""
    if not text:
        return 0
    enc = _encoding_for_model(embedding_model)
    return len(enc.encode(text))


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
    """Zitat-Strip, HTML-Fallback und Whitespace-Normalisierung."""
    text = normalize_body(body, body_html)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@dataclass(frozen=True)
class _TextSegment:
    text: str
    char_start: int
    char_end: int
    token_count: int


def _split_segments(
    body: str,
    *,
    embedding_model: str,
    max_segment_tokens: int,
) -> list[_TextSegment]:
    """Teilt an Absatz- und Satzgrenzen; große Absätze werden weiter gesplittet."""
    if not body.strip():
        return []

    segments: list[_TextSegment] = []
    search_from = 0
    for paragraph in _PARAGRAPH_SPLIT.split(body):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        start = body.find(paragraph, search_from)
        if start < 0:
            start = search_from
        end = start + len(paragraph)
        search_from = end
        tokens = count_tokens(paragraph, embedding_model=embedding_model)
        if tokens <= max_segment_tokens:
            segments.append(
                _TextSegment(
                    text=paragraph,
                    char_start=start,
                    char_end=end,
                    token_count=tokens,
                )
            )
            continue
        sentence_from = start
        for sentence in _SENTENCE_SPLIT.split(paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            s_start = body.find(sentence, sentence_from)
            if s_start < 0:
                s_start = sentence_from
            s_end = s_start + len(sentence)
            sentence_from = s_end
            s_tokens = count_tokens(sentence, embedding_model=embedding_model)
            segments.append(
                _TextSegment(
                    text=sentence,
                    char_start=s_start,
                    char_end=s_end,
                    token_count=s_tokens,
                )
            )
    return segments


def _join_segments(segments: list[_TextSegment], body: str) -> tuple[str, int, int]:
    if not segments:
        return "", 0, 0
    char_start = segments[0].char_start
    char_end = segments[-1].char_end
    return body[char_start:char_end].strip(), char_start, char_end


def _pack_body_chunks(
    body: str,
    segments: list[_TextSegment],
    *,
    max_body_tokens: int,
    overlap_tokens: int,
    min_chunk_tokens: int,
) -> list[tuple[str, int, int]]:
    """Packt Segmente in überlappende Chunks (nur Body, ohne Prefix)."""
    if not segments:
        return []
    if len(segments) == 1 and segments[0].token_count <= max_body_tokens:
        seg = segments[0]
        return [(seg.text, seg.char_start, seg.char_end)]

    packed: list[tuple[str, int, int, int]] = []
    idx = 0
    while idx < len(segments):
        chunk_segments: list[_TextSegment] = []
        used_tokens = 0
        while idx < len(segments):
            seg = segments[idx]
            if chunk_segments and used_tokens + seg.token_count > max_body_tokens:
                break
            if not chunk_segments and seg.token_count > max_body_tokens:
                chunk_segments.append(seg)
                idx += 1
                break
            chunk_segments.append(seg)
            used_tokens += seg.token_count
            idx += 1
        body_text, char_start, char_end = _join_segments(chunk_segments, body)
        packed.append((body_text, char_start, char_end, used_tokens))

        if idx >= len(segments):
            break

        overlap_used = 0
        back_idx = idx
        while back_idx > 0 and overlap_used < overlap_tokens:
            back_idx -= 1
            overlap_used += segments[back_idx].token_count
        if back_idx == idx:
            back_idx = max(0, idx - 1)
        idx = back_idx

    merged: list[tuple[str, int, int]] = [
        (text, start, end) for text, start, end, _ in packed
    ]
    if len(merged) >= 2 and packed[-1][3] < min_chunk_tokens:
        last_text, last_start, last_end, _ = packed[-1]
        prev_text, prev_start, _prev_end = merged[-2]
        merged[-2] = (f"{prev_text}\n\n{last_text}".strip(), prev_start, last_end)
        merged.pop()
    return merged


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
