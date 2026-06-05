"""Tests für semantisches Chunking (Phase 12, ohne Re-Ranking)."""

from __future__ import annotations

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.ai.services.semantic_chunking import (
    build_context_prefix,
    count_tokens,
    preprocess_mail_body,
    semantic_chunk,
)


def _long_body(paragraphs: int = 12, words_per_paragraph: int = 80) -> str:
    parts = []
    for i in range(paragraphs):
        words = [f"paragraph{i}word{j}" for j in range(words_per_paragraph)]
        parts.append(" ".join(words))
    return "\n\n".join(parts)


def test_short_mail_single_chunk() -> None:
    """Kurze Mails ergeben genau einen Chunk."""
    body = "Guten Tag, ich möchte meine Buchung AB123 stornieren."
    chunks = semantic_chunk(
        body,
        subject="Stornierung",
        max_tokens=512,
        overlap_tokens=64,
    )
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert "Stornierung" in chunks[0].text
    assert body in chunks[0].text


def test_long_mail_multiple_chunks() -> None:
    """Lange Mails werden in mehrere Chunks gesplittet."""
    body = _long_body(paragraphs=20, words_per_paragraph=60)
    chunks = semantic_chunk(
        body,
        max_tokens=128,
        overlap_tokens=16,
    )
    assert len(chunks) > 1
    assert all(chunk.chunk_index == i for i, chunk in enumerate(chunks))


def test_token_limit_respected() -> None:
    """Jeder Chunk bleibt unter dem konfigurierten Token-Limit."""
    body = _long_body()
    max_tokens = 200
    chunks = semantic_chunk(
        body,
        max_tokens=max_tokens,
        overlap_tokens=32,
    )
    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.token_count <= max_tokens


def test_overlap_between_chunks() -> None:
    """Benachbarte Chunks teilen sich Text am Übergang."""
    body = _long_body(paragraphs=10, words_per_paragraph=50)
    chunks = semantic_chunk(
        body,
        max_tokens=120,
        overlap_tokens=24,
    )
    assert len(chunks) >= 2
    first_tail = chunks[0].body_text[-80:].strip()
    second_head = chunks[1].body_text[:120].strip()
    assert first_tail
    assert any(token in second_head for token in first_tail.split()[-3:])


def test_strip_quoted_history() -> None:
    """Zitierte Antwort-Historie wird vor dem Chunking entfernt."""
    body = "Neue Anfrage zur Buchung.\n\nOn Mon, Jun 1 wrote:\n> alte Mail"
    chunks = semantic_chunk(body)
    assert len(chunks) == 1
    assert "Neue Anfrage" in chunks[0].body_text
    assert "alte Mail" not in chunks[0].body_text


def test_context_prefix_from_extraction() -> None:
    """Kontext-Prefix enthält Betreff, Intent und Extraktionsfelder."""
    extraction = BookingExtraction(
        intent=BookingIntent.CANCELLATION,
        property_name="Haus am See",
        booking_number="AB999",
    )
    prefix = build_context_prefix(
        subject="Storno bitte",
        intent=extraction.intent.value if extraction.intent else None,
        property_name=extraction.property_name,
        booking_number=extraction.booking_number,
    )
    chunks = semantic_chunk(
        "Bitte stornieren.",
        subject="Storno bitte",
        extraction=extraction,
    )
    assert "Storno bitte" in prefix
    assert "cancellation" in prefix
    assert "Haus am See" in prefix
    assert "AB999" in prefix
    assert chunks[0].context_prefix == prefix
    assert prefix in chunks[0].text


def test_preprocess_normalizes_whitespace() -> None:
    """Mehrfache Leerzeilen werden normalisiert."""
    body = "Zeile eins\n\n\n\nZeile zwei"
    assert preprocess_mail_body(body) == "Zeile eins\n\nZeile zwei"


def test_empty_body_returns_no_chunks() -> None:
    """Leerer Body liefert keine Chunks."""
    assert semantic_chunk("   \n\n  ") == []


def test_count_tokens_matches_encoder() -> None:
    """Token-Zählung ist konsistent für kurze Texte."""
    text = "hello world"
    assert count_tokens(text) >= 2
