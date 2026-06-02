"""Feld-für-Feld-Vergleich für Offline-Evals."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from schemas.booking.extraction import BookingExtraction
from schemas.booking.taxonomy import BookingIntent


@dataclass
class FieldCompareResult:
    """Ergebnis eines Einzelfeld-Vergleichs."""

    field: str
    expected: Any
    actual: Any
    matched: bool


@dataclass
class CaseExtractionResult:
    """Extraktions-Eval für einen Fall."""

    message_id: str
    field_results: list[FieldCompareResult] = field(default_factory=list)

    @property
    def matched_fields(self) -> int:
        return sum(1 for r in self.field_results if r.matched)

    @property
    def total_fields(self) -> int:
        return len(self.field_results)

    @property
    def case_passed(self) -> bool:
        return self.total_fields > 0 and self.matched_fields == self.total_fields


@dataclass
class ExtractionEvalReport:
    """Aggregierte Trefferquoten über alle Fälle."""

    case_results: list[CaseExtractionResult] = field(default_factory=list)

    @property
    def cases_with_expectation(self) -> int:
        return len(self.case_results)

    @property
    def cases_passed(self) -> int:
        return sum(1 for c in self.case_results if c.case_passed)

    @property
    def field_matched(self) -> int:
        return sum(c.matched_fields for c in self.case_results)

    @property
    def field_total(self) -> int:
        return sum(c.total_fields for c in self.case_results)

    @property
    def case_hit_rate(self) -> float:
        if self.cases_with_expectation == 0:
            return 1.0
        return self.cases_passed / self.cases_with_expectation

    @property
    def field_accuracy(self) -> float:
        if self.field_total == 0:
            return 1.0
        return self.field_matched / self.field_total

    def summary_line(self, mode: str) -> str:
        """Eine Zeile für pytest -s / Logs."""
        note = "wiring_regression" if mode == "mock" else "extraction_quality_live"
        return (
            f"OFFLINE_EVAL mode={mode} note={note} "
            f"field_accuracy={self.field_accuracy:.2f} "
            f"({self.field_matched}/{self.field_total} fields) "
            f"case_hit_rate={self.case_hit_rate:.2f} "
            f"({self.cases_passed}/{self.cases_with_expectation} cases)"
        )


def _normalize_expected_value(key: str, value: Any) -> Any:
    if key == "intent" and isinstance(value, str):
        return BookingIntent(value).value
    return value


def _normalize_actual_value(key: str, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if key in ("check_in", "check_out") and hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "isoformat") and key == "timestamp":
        return value.isoformat()
    return value


def compare_extraction(
    actual: BookingExtraction,
    expected: dict[str, Any],
    message_id: str,
) -> CaseExtractionResult:
    """Vergleicht nur Keys aus expected (Feld-für-Feld, exakt)."""
    dumped = actual.model_dump(mode="json")
    results: list[FieldCompareResult] = []
    for key, exp_raw in expected.items():
        exp_val = _normalize_expected_value(key, exp_raw)
        act_val = _normalize_actual_value(key, dumped.get(key))
        results.append(
            FieldCompareResult(
                field=key,
                expected=exp_val,
                actual=act_val,
                matched=act_val == exp_val,
            )
        )
    return CaseExtractionResult(message_id=message_id, field_results=results)


def run_extraction_eval(
    cases: list[dict[str, object]],
    extract_fn: Any,
) -> ExtractionEvalReport:
    """Führt Extraktion pro Fall aus und vergleicht expected_extraction."""
    from datetime import datetime

    from models.email import StoredEmail
    from schemas.booking.taxonomy import BookingIntent

    report = ExtractionEvalReport()
    for case in cases:
        expected_ext = case.get("expected_extraction")
        if not expected_ext or not isinstance(expected_ext, dict):
            continue
        email = StoredEmail(
            message_id=str(case["message_id"]),
            from_address=str(case["from_address"]),
            subject=str(case["subject"]),
            body_text=str(case["body_text"]),
            received_at=datetime.fromisoformat(
                str(case["received_at"]).replace("Z", "+00:00")
            ),
            platform=case.get("platform"),  # type: ignore[arg-type]
        )
        intent = None
        if "expected_intent" in case:
            intent = BookingIntent(str(case["expected_intent"]))
        actual = extract_fn(email, intent=intent)
        report.case_results.append(
            compare_extraction(
                actual,
                expected_ext,
                str(case["message_id"]),
            )
        )
    return report
