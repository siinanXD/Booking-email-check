"""Abgleich extrahierter Unterkunftsnamen mit dem Mandanten-Katalog."""

from __future__ import annotations

import re


def _normalize(value: str) -> str:
    """Kleinschreibung + Whitespace zusammenfassen für robusten Vergleich."""
    return " ".join(value.split()).lower()


def _contains_as_words(haystack: str, needle: str) -> bool:
    """`needle` als ganze Wortfolge in `haystack` (an Wortgrenzen)."""
    pattern = r"(?<!\S)" + re.escape(needle) + r"(?!\S)"
    return re.search(pattern, haystack) is not None


def match_known_property_name(
    candidate: str | None,
    known_names: list[str],
) -> str | None:
    """Findet den passenden Katalog-Namen (case-insensitive, wortgenau).

    Reihenfolge:
    1. Exakter Treffer (normalisiert) gewinnt.
    2. Sonst: Katalog-Name kommt als **ganze Wortfolge** im (längeren)
       Kandidaten vor — der **spezifischste (längste)** Treffer gewinnt.

    Bewusst NICHT: Kandidat als Teilstring des Katalog-Namens. Ein generisches
    ``Zimmer`` würde sonst auf ``Zimmer Nummer drei`` gemappt — jede Mail
    bekäme dieselbe (falsche) Unterkunft.
    """
    raw = (candidate or "").strip()
    if not raw or not known_names:
        return None
    low = _normalize(raw)

    for name in known_names:
        if _normalize(name) == low:
            return name

    best: str | None = None
    best_len = 0
    for name in known_names:
        key = _normalize(name)
        if not key:
            continue
        if _contains_as_words(low, key) and len(key) > best_len:
            best = name
            best_len = len(key)
    return best
