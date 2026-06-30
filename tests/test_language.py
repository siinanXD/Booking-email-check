"""Antwortsprache-Erkennung (langdetect + Heuristik-Rückfall)."""

from __future__ import annotations

from backend.core.utils.language import detect_reply_language


def test_clear_german() -> None:
    text = "Hallo, vielen Dank für Ihre Buchung. Wir freuen uns auf Ihre Anreise."
    assert detect_reply_language(text) == "de"


def test_clear_english() -> None:
    text = "Hello, thank you for your booking. We look forward to your arrival."
    assert detect_reply_language(text) == "en"


def test_short_english_falls_back_to_heuristic() -> None:
    # langdetect verschätzt sich auf kurzem Text gern → Heuristik rettet de/en.
    assert detect_reply_language("Hello, I would like to book a room") == "en"


def test_empty_defaults_to_german() -> None:
    assert detect_reply_language("") == "de"
    assert detect_reply_language(None) == "de"
    assert detect_reply_language("   ") == "de"


def test_umlauts_signal_german() -> None:
    assert detect_reply_language("Grüße und schöne Anreise") == "de"
