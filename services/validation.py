"""Domänen-Validierung für Extraktionen."""

from __future__ import annotations

from dataclasses import dataclass, field

from schemas.booking.extraction import BookingExtraction
from schemas.booking.taxonomy import BookingIntent


@dataclass
class ValidationResult:
    """Ergebnis der Validierung."""

    valid: bool
    errors: list[str] = field(default_factory=list)


class ValidationService:
    """Pydantic + fachliche Regeln."""

    _REQUIRED_BY_INTENT: dict[BookingIntent, list[str]] = {
        BookingIntent.NEW_BOOKING: ["check_in", "check_out"],
        BookingIntent.CANCELLATION: ["booking_number"],
        BookingIntent.CHANGE: ["booking_number"],
        BookingIntent.PAYMENT_ISSUE: ["booking_number"],
    }

    def validate(self, extraction: BookingExtraction) -> ValidationResult:
        """Prüft Extraktion inkl. Datumslogik."""
        errors: list[str] = []
        if (
            extraction.check_in
            and extraction.check_out
            and extraction.check_out <= extraction.check_in
        ):
            errors.append("check_out must be after check_in")

        intent = extraction.intent or BookingIntent.OTHER
        for field_name in self._REQUIRED_BY_INTENT.get(intent, []):
            if getattr(extraction, field_name, None) is None:
                errors.append(f"missing required field: {field_name}")

        return ValidationResult(valid=len(errors) == 0, errors=errors)
