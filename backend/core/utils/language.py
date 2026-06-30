"""Sprach-Erkennung (DE/EN) für die Antwortsprache.

langdetect liefert auf längeren Texten zuverlässig — bei sehr kurzen/gemischten
Texten aber auch mal Unsinn (z. B. „af" für klares Englisch). Daher: langdetect
zuerst, und nur wenn es eindeutig de/en sagt; sonst die DE/EN-Stopword-Heuristik
als Rückfall.
"""

from __future__ import annotations

import re

from langdetect import DetectorFactory, detect

# Deterministisch (gleicher Text → gleiches Ergebnis).
DetectorFactory.seed = 0

_DE_MARKERS = {
    "der",
    "die",
    "das",
    "und",
    "ich",
    "sie",
    "wir",
    "ist",
    "nicht",
    "mit",
    "für",
    "auf",
    "buchung",
    "gast",
    "zimmer",
    "anreise",
    "vielen",
    "dank",
    "bitte",
    "freundlichen",
    "grüßen",
    "hallo",
    "guten",
    "möchte",
    "wäre",
}
_EN_MARKERS = {
    "the",
    "and",
    "you",
    "your",
    "is",
    "are",
    "for",
    "with",
    "booking",
    "guest",
    "room",
    "arrival",
    "thanks",
    "thank",
    "please",
    "regards",
    "hello",
    "would",
    "could",
    "we",
    "i",
}

_WORD_RE = re.compile(r"[a-zA-Zäöüß]+")


def detect_reply_language(text: str | None) -> str:
    """Gibt "de" oder "en" zurück; Standard "de" bei Gleichstand/leer."""
    if not text or not text.strip():
        return "de"
    try:
        code = detect(text)
    except Exception:  # noqa: BLE001 - LangDetectException o. Ä. → Heuristik
        code = ""
    if code == "de":
        return "de"
    if code == "en":
        return "en"
    return _heuristic_language(text)


def _heuristic_language(text: str) -> str:
    """DE/EN-Stopword-Heuristik als Rückfall für kurze/gemischte Texte."""
    words = [w.lower() for w in _WORD_RE.findall(text)]
    if not words:
        return "de"
    de = sum(1 for w in words if w in _DE_MARKERS)
    en = sum(1 for w in words if w in _EN_MARKERS)
    # Umlaute sind ein starkes DE-Signal.
    if any(ch in text for ch in "äöüß"):
        de += 1
    return "en" if en > de else "de"
