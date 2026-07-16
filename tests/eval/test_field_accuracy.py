"""Regressionsschutz: deterministische Feldgenauigkeit auf dem Golden-Set.

Läuft ohne LLM (CI-tauglich) und sichert die Zimmer/Kanal-Extraktion aus
Ticket 1 über alle Kanäle ab.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.ai.eval.field_accuracy import evaluate_deterministic


def _golden() -> list[dict[str, Any]]:
    path = Path(__file__).parent / "extraction_golden.json"
    data: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return data


def test_deterministic_field_accuracy_is_perfect() -> None:
    report = evaluate_deterministic(_golden())
    # Jeder Fall muss gemessen werden — keine feste Zahl, sonst bremst die
    # Zusicherung nur das Ergänzen neuer Fälle aus.
    assert report.cases == len(_golden())
    # render_table() als Fehlermeldung → zeigt direkt die abweichenden Felder.
    assert report.overall.accuracy == 1.0, "\n" + report.render_table()


def test_every_channel_covered_and_perfect() -> None:
    report = evaluate_deterministic(_golden())
    assert set(report.per_channel) == {"booking.com", "airbnb", "direkt"}
    for channel, stat in report.per_channel.items():
        assert stat.accuracy == 1.0, f"{channel}: {stat.matched}/{stat.total}"


def test_room_and_channel_fields_measured() -> None:
    report = evaluate_deterministic(_golden())
    assert "room_number" in report.per_field
    assert "channel" in report.per_field
    # Zimmer und Kanal gehören in JEDEN Fall — sonst schleicht sich ein Fall
    # ein, der die beiden kritischen Felder gar nicht prüft.
    assert report.per_field["room_number"].total == report.cases
    assert report.per_field["channel"].total == report.cases


def test_html_only_mail_wird_abgedeckt() -> None:
    """beds24-Mails sind oft HTML; der Text-Teil kann die Zimmer-Zeile verlieren.

    Genau dieser Pfad war im Golden-Set nie abgedeckt — `_email_from_case`
    reichte `body_html` nicht durch, obwohl `_enrich_room_and_channel` es liest.
    """
    html_only = [c for c in _golden() if c.get("body_html") and not c.get("body_text")]
    assert html_only, "Kein Fall, der die Zimmer-Zeile nur im HTML trägt"

    report = evaluate_deterministic(html_only)

    assert report.overall.accuracy == 1.0, "\n" + report.render_table()


def test_property_matching_wird_abgedeckt() -> None:
    """Ohne Katalog lief das Property-Matching im Eval nie mit.

    Dort entstanden die Phantom-Objekte ("Münzbach Ferienzimmer Zimmer Nr. 3"),
    weil das LLM das Zimmer in den Objektnamen faltet.
    """
    with_catalog = [
        c
        for c in _golden()
        if c.get("known_properties") and "property_name" in (c.get("expected") or {})
    ]
    assert with_catalog, "Kein Fall prüft die Rückführung auf den Objektkatalog"

    report = evaluate_deterministic(with_catalog)

    assert report.overall.accuracy == 1.0, "\n" + report.render_table()
