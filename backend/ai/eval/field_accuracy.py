"""Feld-Genauigkeit der deterministischen Extraktions-Anreicherung.

Misst die in ``enrich_extraction`` deterministisch befüllten Felder
(z. B. ``room_number``, ``channel``) über ein Golden-Set — pro Feld und pro
Kanal. Läuft ohne LLM/Kosten und eignet sich damit für CI + Regressionsschutz
(genau die Schicht, in der der Zimmer/Kanal-Bug aus Ticket 1 lebte).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.extraction_enrichment import enrich_extraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.models.email import StoredEmail


@dataclass
class FieldStat:
    """Treffer/Gesamt für ein einzelnes Feld."""

    matched: int = 0
    total: int = 0

    @property
    def accuracy(self) -> float:
        return self.matched / self.total if self.total else 1.0


@dataclass
class Mismatch:
    """Ein abweichendes Feld (für die Fehleranzeige)."""

    case_id: str
    channel: str
    field: str
    expected: Any
    actual: Any


@dataclass
class FieldAccuracyReport:
    """Aggregierte Feld-Genauigkeit, pro Feld und pro Kanal."""

    per_field: dict[str, FieldStat] = field(default_factory=dict)
    per_channel: dict[str, FieldStat] = field(default_factory=dict)
    mismatches: list[Mismatch] = field(default_factory=list)
    cases: int = 0

    @property
    def overall(self) -> FieldStat:
        agg = FieldStat()
        for stat in self.per_field.values():
            agg.matched += stat.matched
            agg.total += stat.total
        return agg

    def _tally(self, channel: str, fname: str, ok: bool) -> None:
        for bucket, key in ((self.per_field, fname), (self.per_channel, channel)):
            stat = bucket.setdefault(key, FieldStat())
            stat.total += 1
            stat.matched += 1 if ok else 0

    def render_table(self) -> str:
        """Lesbarer Report (Per-Feld + Per-Kanal + Fehler)."""
        lines = [
            "FIELD-ACCURACY (deterministisch, ohne LLM)",
            f"  Fälle: {self.cases}   "
            f"Gesamt: {self.overall.accuracy:.0%} "
            f"({self.overall.matched}/{self.overall.total} Felder)",
            "  — pro Feld —",
        ]
        for name in sorted(self.per_field):
            s = self.per_field[name]
            lines.append(f"    {name:<14} {s.accuracy:>5.0%}  ({s.matched}/{s.total})")
        lines.append("  — pro Kanal —")
        for name in sorted(self.per_channel):
            s = self.per_channel[name]
            lines.append(f"    {name:<14} {s.accuracy:>5.0%}  ({s.matched}/{s.total})")
        if self.mismatches:
            lines.append("  — Abweichungen —")
            for m in self.mismatches:
                lines.append(
                    f"    [{m.case_id}/{m.channel}] {m.field}: "
                    f"erwartet={m.expected!r} ist={m.actual!r}"
                )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cases": self.cases,
            "overall_accuracy": round(self.overall.accuracy, 4),
            "per_field": {
                k: {
                    "accuracy": round(v.accuracy, 4),
                    "matched": v.matched,
                    "total": v.total,
                }
                for k, v in self.per_field.items()
            },
            "per_channel": {
                k: {
                    "accuracy": round(v.accuracy, 4),
                    "matched": v.matched,
                    "total": v.total,
                }
                for k, v in self.per_channel.items()
            },
            "mismatches": [
                {
                    "case_id": m.case_id,
                    "channel": m.channel,
                    "field": m.field,
                    "expected": m.expected,
                    "actual": m.actual,
                }
                for m in self.mismatches
            ],
        }


def _email_from_case(case: dict[str, Any]) -> StoredEmail:
    raw = case.get("received_at") or "2026-01-01T00:00:00Z"
    received = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if received.tzinfo is None:
        received = received.replace(tzinfo=UTC)
    return StoredEmail(
        message_id=str(case.get("id", "case")),
        from_address=str(case.get("from_address", "")),
        subject=str(case.get("subject", "")),
        body_text=str(case.get("body_text", "")),
        # beds24-Mails sind oft HTML; der Text-Teil kann die Zimmer-Zeile
        # verlieren. `_enrich_room_and_channel` liest deshalb body_html mit —
        # ohne Durchreichen hier bliebe genau dieser Pfad ungetestet.
        body_html=case.get("body_html"),
        received_at=received,
        correlation_id=str(case.get("id", "case")),
        platform=case.get("platform"),
    )


def _base_extraction(case: dict[str, Any]) -> BookingExtraction:
    base = dict(case.get("base") or {})
    intent = base.pop("intent", None)
    if isinstance(intent, str):
        base["intent"] = BookingIntent(intent)
    elif intent is not None:
        base["intent"] = intent
    return BookingExtraction.model_validate(base)


def evaluate_deterministic(cases: list[dict[str, Any]]) -> FieldAccuracyReport:
    """Wertet das Golden-Set über ``enrich_extraction`` aus (ohne LLM)."""
    report = FieldAccuracyReport()
    for case in cases:
        expected = case.get("expected")
        if not isinstance(expected, dict) or not expected:
            continue
        report.cases += 1
        channel = str(case.get("channel_group", "unbekannt"))
        # `known_properties` optional pro Fall: ohne Katalog läuft das
        # Property-Matching gar nicht — genau dort entstanden die Phantom-
        # Objekte ("Münzbach Ferienzimmer Zimmer Nr. 3").
        known = [str(n) for n in (case.get("known_properties") or [])] or None
        enriched = enrich_extraction(
            _email_from_case(case),
            _base_extraction(case),
            known_property_names=known,
        )
        dumped = enriched.model_dump(mode="json")
        for fname, exp in expected.items():
            actual = dumped.get(fname)
            ok = actual == exp
            report._tally(channel, fname, ok)
            if not ok:
                report.mismatches.append(
                    Mismatch(str(case.get("id", "?")), channel, fname, exp, actual)
                )
    return report
