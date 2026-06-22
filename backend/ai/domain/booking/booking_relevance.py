"""Erkennung echter Buchungs-Mails vs. irrelevante Post."""

from __future__ import annotations

import re
from typing import NamedTuple

from backend.ai.domain.booking._booking_patterns import (
    _BEDS24_SUBJECT_RE,
    _BOOKING_INTENTS,
    _BOOKING_SIGNAL_RE,
    _FAKE_BOOKING_NUMBER_RE,
    _NOISE_SENDER_SUBSTRINGS,
    _NOISE_SUBJECT_PATTERNS,
    _NON_BOOKING_SUBJECT_RE,
    _from_domain,
)
from backend.ai.domain.booking._booking_patterns import (
    _TRUSTED_BOOKING_DOMAINS as _TRUSTED_BOOKING_DOMAINS,
)
from backend.ai.domain.booking._booking_patterns import (
    EmailLike as EmailLike,
)
from backend.ai.domain.booking._booking_patterns import (
    has_reservation_request_signals as has_reservation_request_signals,
)
from backend.ai.domain.booking._booking_patterns import (
    has_text_booking_signals as has_text_booking_signals,
)
from backend.ai.domain.booking._booking_patterns import (
    is_marketing_noise as is_marketing_noise,
)
from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent


class BookingMailVerdict(NamedTuple):
    """Ergebnis der Booking-Prüfung."""

    is_booking: bool
    reason: str


def has_extraction_booking_context(extraction: BookingExtraction | None) -> bool:
    """Extraktion enthält nutzbare Buchungs-/Gastdaten (unabhängig von PMS)."""
    if extraction is None:
        return False
    if extraction.booking_number and str(extraction.booking_number).strip():
        return True
    if extraction.property_name and str(extraction.property_name).strip():
        return True
    if extraction.guest_name and str(extraction.guest_name).strip():
        low = str(extraction.guest_name).strip().lower()
        if low not in ("gast", "guest", "unbekannt", "unknown"):
            return True
    if extraction.check_in or extraction.check_out:
        return True
    if extraction.email and "@" in str(extraction.email):
        return True
    return False


def is_probable_non_booking_mail(email: EmailLike) -> bool:
    """Offensichtlich keine Buchungsmail (vor LLM)."""
    if is_marketing_noise(email):
        return True
    subject = email.subject or ""
    if _NON_BOOKING_SUBJECT_RE.search(subject):
        return True
    from_addr = (email.from_address or "").lower()
    if "beds24" in from_addr or "bookings@" in from_addr:
        return False
    if _BEDS24_SUBJECT_RE.match(subject.strip()):
        return False
    domain = _from_domain(email.from_address)
    if any(d in domain for d in _TRUSTED_BOOKING_DOMAINS):
        return False
    return False


def is_probable_booking_mail(email: EmailLike) -> bool:
    """Heuristik: sehr wahrscheinlich Buchungs-/Gast-Mail (Beds24 & Co.)."""
    if is_probable_non_booking_mail(email):
        return False
    from_addr = (email.from_address or "").lower()
    subject = (email.subject or "").strip()
    platform = (email.platform or "").lower()
    if "beds24" in from_addr or "bookings@beds24" in from_addr:
        return True
    if "beds24" in platform:
        return True
    if _BEDS24_SUBJECT_RE.match(subject):
        return True
    domain = _from_domain(email.from_address)
    if any(known in domain for known in _TRUSTED_BOOKING_DOMAINS):
        return _BOOKING_SIGNAL_RE.search(subject) is not None
    return has_text_booking_signals(email)


def is_plausible_booking_number(
    booking_number: str | None,
    email: EmailLike,
) -> bool:
    """Buchungsnummer glaubwürdig (kein LLM-Platzhalter)."""
    if not booking_number:
        return False
    bn = str(booking_number).strip()
    if not bn or bn.lower() in ("null", "none", "-"):
        return False
    if _FAKE_BOOKING_NUMBER_RE.match(bn) and not is_probable_booking_mail(email):
        return False
    if re.match(r"^\d{5,}$", bn):
        return True
    if is_probable_booking_mail(email):
        return len(bn) >= 4
    return False


def has_booking_signals(
    email: EmailLike,
    extraction: BookingExtraction | None,
) -> bool:
    """Betreff/Absender/Extraktion deuten auf Buchungskontext."""
    if has_reservation_request_signals(email):
        return True
    if has_extraction_booking_context(extraction):
        return True
    if is_plausible_booking_number(
        extraction.booking_number if extraction else None,
        email,
    ):
        return True
    if is_probable_booking_mail(email):
        return True
    platform = (email.platform or "").lower()
    if extraction and extraction.platform:
        platform = platform or str(extraction.platform).lower()
    if platform and any(p in platform for p in ("beds24", "airbnb", "booking", "vrbo")):
        return True
    domain = _from_domain(email.from_address)
    if any(known in domain for known in _TRUSTED_BOOKING_DOMAINS):
        combined = f"{email.subject}\n{email.body_text or ''}"
        return bool(_BOOKING_SIGNAL_RE.search(combined))
    return False


def infer_beds24_intent(subject: str) -> BookingIntent | None:
    """Leitet Intent aus typischen Beds24-Betreffzeilen ab (Fallback bei LLM=other)."""
    subject_line = (subject or "").strip()
    if re.match(r"^Buchung\s*:", subject_line, re.IGNORECASE):
        return BookingIntent.NEW_BOOKING
    if re.match(r"^Stornierung\s*:", subject_line, re.IGNORECASE):
        return BookingIntent.CANCELLATION
    if re.match(r"^Buchungsänderung\s*:", subject_line, re.IGNORECASE):
        return BookingIntent.CHANGE
    if re.match(r"^Nachricht vom Gast\s*:", subject_line, re.IGNORECASE):
        return BookingIntent.GUEST_INQUIRY
    return None


def effective_booking_intent(
    email: EmailLike,
    extraction: BookingExtraction | None,
) -> BookingIntent | None:
    """Intent für Listen/Review: Extraktion, LLM-Klassifikation, Beds24-Betreff."""
    if extraction and extraction.intent and extraction.intent != BookingIntent.OTHER:
        return extraction.intent
    inferred = infer_beds24_intent(email.subject or "")
    if inferred is not None:
        return inferred
    if has_reservation_request_signals(email):
        return BookingIntent.NEW_BOOKING
    if extraction and extraction.intent:
        return extraction.intent
    return None


def classify_booking_mail(
    email: EmailLike,
    extraction: BookingExtraction | None = None,
) -> BookingMailVerdict:
    """Zentrale Entscheidung: echte Buchungsmail ja/nein."""
    if is_probable_non_booking_mail(email):
        return BookingMailVerdict(False, "non_booking_heuristic")
    if is_marketing_noise(email):
        return BookingMailVerdict(False, "marketing_noise")
    if extraction is not None and extraction.intent is not None:
        if extraction.intent not in _BOOKING_INTENTS:
            # LLM sagt z. B. "other" – aber ein eindeutiger PMS-/Beds24-Betreff
            # ("Buchung:", "Stornierung:", …) ist ein stärkeres Signal als die
            # LLM-Fehlklassifikation. Dann trotzdem als Buchung behandeln.
            if infer_beds24_intent(email.subject or "") is not None:
                return BookingMailVerdict(True, "pms_subject_overrides_other")
            return BookingMailVerdict(False, f"intent_{extraction.intent.value}")
        if extraction.intent == BookingIntent.NEW_BOOKING:
            return BookingMailVerdict(True, "llm_new_booking")
        if extraction.intent == BookingIntent.CHANGE:
            if is_plausible_booking_number(
                extraction.booking_number, email
            ) or has_booking_signals(email, extraction):
                return BookingMailVerdict(True, "llm_change")
            return BookingMailVerdict(False, "change_no_proof")
        if extraction.intent == BookingIntent.GUEST_INQUIRY:
            if has_booking_signals(email, extraction):
                return BookingMailVerdict(True, "guest_inquiry_with_signals")
            return BookingMailVerdict(False, "guest_inquiry_no_signals")
        if extraction.intent == BookingIntent.CANCELLATION:
            if is_plausible_booking_number(extraction.booking_number, email):
                return BookingMailVerdict(True, "cancellation_with_booking_no")
            if is_probable_booking_mail(email):
                return BookingMailVerdict(True, "cancellation_pms_subject")
            return BookingMailVerdict(False, "cancellation_no_proof")
        if has_booking_signals(email, extraction):
            return BookingMailVerdict(True, f"intent_{extraction.intent.value}")
        return BookingMailVerdict(False, "intent_without_signals")
    if is_probable_booking_mail(email):
        return BookingMailVerdict(True, "beds24_or_pms_heuristic")
    if has_reservation_request_signals(email):
        return BookingMailVerdict(True, "reservation_request_heuristic")
    return BookingMailVerdict(False, "no_extraction")


def is_booking_relevant(
    email: EmailLike,
    extraction: BookingExtraction | None,
) -> bool:
    """Kompatibilitäts-Wrapper für Listen/Review."""
    return classify_booking_mail(email, extraction).is_booking


def relevance_fields(
    email: EmailLike,
    extraction: BookingExtraction | None,
) -> dict[str, object]:
    """Persistierbare Relevanz-Felder (`is_booking`, `effective_intent`).

    Quelle der Wahrheit für die schnellen Kategorie-Listen. Wird beim
    Extrahieren geschrieben und vom Backfill-Skript neu berechnet.
    """
    verdict = classify_booking_mail(email, extraction)
    intent = effective_booking_intent(email, extraction)
    return {
        "is_booking": verdict.is_booking,
        "effective_intent": intent.value if intent else None,
    }


def mongo_noise_exclusion() -> dict[str, object]:
    """Mongo-$match: Marketing-Mails ausschließen."""
    nor: list[dict[str, object]] = []
    for frag in _NOISE_SENDER_SUBSTRINGS:
        nor.append({"from_address": {"$regex": re.escape(frag), "$options": "i"}})
    for pattern in _NOISE_SUBJECT_PATTERNS:
        nor.append({"subject": {"$regex": pattern.pattern, "$options": "i"}})
    nor.append(
        {"subject": {"$regex": _NON_BOOKING_SUBJECT_RE.pattern, "$options": "i"}}
    )
    if not nor:
        return {}
    return {"$nor": nor}
