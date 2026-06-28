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
    assert report.cases == 6
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
    assert report.per_field["room_number"].total == 6
