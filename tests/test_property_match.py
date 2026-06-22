"""Tests für Unterkunfts-Abgleich."""

from __future__ import annotations

from backend.ai.domain.booking.property_match import match_known_property_name


def test_match_known_property_substring() -> None:
    assert (
        match_known_property_name(
            "Unser Ferienhaus Nord bitte",
            ["Ferienhaus Nord"],
        )
        == "Ferienhaus Nord"
    )


def test_exact_match_case_insensitive() -> None:
    assert (
        match_known_property_name("ferienhaus  nord", ["Ferienhaus Nord"])
        == "Ferienhaus Nord"
    )


def test_generic_candidate_does_not_map_to_specific_property() -> None:
    """Regression: kurzer/generischer Name darf NICHT auf einen längeren
    Katalog-Eintrag gemappt werden (sonst landet jede Mail auf demselben)."""
    assert match_known_property_name("Zimmer", ["Zimmer Nummer drei"]) is None


def test_no_partial_word_match() -> None:
    assert match_known_property_name("Ferienhausen West", ["Ferienhaus"]) is None


def test_longest_match_wins() -> None:
    known = ["Haus", "Haus am See"]
    assert (
        match_known_property_name("Buchung Haus am See für Anna", known)
        == "Haus am See"
    )


def test_no_match_returns_none() -> None:
    assert match_known_property_name("Strandvilla", ["Ferienhaus Nord"]) is None
