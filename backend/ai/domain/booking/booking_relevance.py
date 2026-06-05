"""Erkennung echter Buchungs-Mails vs. irrelevante Post."""

from __future__ import annotations

import re
from typing import NamedTuple

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.models.email import IncomingEmail, StoredEmail

EmailLike = IncomingEmail | StoredEmail

# --- Absender / Betreff: klar KEINE Buchungsmail ---
_NOISE_SENDER_SUBSTRINGS = (
    "comigo",
    "lumigita",
    "lomigata",
    "newsletter",
    "mailchimp",
    "sendgrid.net",
    "constantcontact",
    "linkedin.com",
    "github.com",
    "temu.com",
    "amazon.",
    "haystack",
    "indeed.",
    "xing.com",
    "stepstone",
    "nvidia.com",
    "microsoft.com",
    "notifications@",
    "noreply@notify",
)

_NON_BOOKING_SUBJECT_RE = re.compile(
    r"(prime\s*day|temu|linkedin|github|run\s+failed|ci\s*-|codex|haystack|"
    r"software\s+engineer|kontaktanfrage|cv\s+und|bestellung\s+wurde|"
    r"zugriffstoken|widerrufen|elektroingenieur|standpunkt|belohnung|"
    r"ankünfte\s+in\s+möbeln|maintanace|emoji|temu-bellet)",
    re.IGNORECASE,
)

_NOISE_SUBJECT_PATTERNS = (
    re.compile(r"\bcomigo\b", re.IGNORECASE),
    re.compile(r"\blumigita\b", re.IGNORECASE),
    re.compile(r"\bnewsletter\b", re.IGNORECASE),
    re.compile(r"\bwerbung\b", re.IGNORECASE),
    re.compile(r"\bunsubscribe\b", re.IGNORECASE),
)

# Beds24 / PMS — starke Indikatoren
_BEDS24_SUBJECT_RE = re.compile(
    r"^(Buchung|Stornierung|Buchungsänderung|Nachricht vom Gast)\s*:",
    re.IGNORECASE,
)

_BOOKING_SIGNAL_RE = re.compile(
    r"(buchung|booking|reservierung|storno|stornierung|cancel|"
    r"beds24|airbnb|booking\.com|vrbo|expedia|münzbach|muenzbach|"
    r"ferienzimmer|zimmer\s+nr|gäste|guest|anreise|abreise|übernacht)",
    re.IGNORECASE,
)

# Gast-Anfrage ohne PMS-Betreff (z. B. „ich möchte buchen“)
_RESERVATION_REQUEST_RE = re.compile(
    r"(möchte\s+(gerne\s+)?(eine\s+)?buchung|würde\s+gerne\s+.*buchung|"
    r"buchung\s+tätigen|zimmer\s+reservieren|reservierung\s+anfragen|"
    r"would\s+like\s+to\s+(make\s+a\s+)?book|like\s+to\s+book|"
    r"book\s+a\s+room|make\s+a\s+reservation|availability|verfügbarkeit)",
    re.IGNORECASE,
)

_TRUSTED_BOOKING_DOMAINS = (
    "beds24.com",
    "beds24.de",
    "airbnb.com",
    "booking.com",
    "guest.booking.com",
    "expedia.com",
    "vrbo.com",
)

# LLM erfindet oft AB200 / XY999 bei Werbe-Mails
_FAKE_BOOKING_NUMBER_RE = re.compile(r"^[A-Z]{2}\d{2,4}$", re.IGNORECASE)

_BOOKING_INTENTS = frozenset(
    {
        BookingIntent.NEW_BOOKING,
        BookingIntent.CHANGE,
        BookingIntent.CANCELLATION,
        BookingIntent.GUEST_INQUIRY,
    }
)


class BookingMailVerdict(NamedTuple):
    """Ergebnis der Booking-Prüfung."""

    is_booking: bool
    reason: str


def _from_domain(from_address: str) -> str:
    if "@" not in from_address:
        return ""
    return from_address.split("@")[-1].lower().strip()


def is_trusted_booking_domain(from_address: str) -> bool:
    """Absender-Domain gehört zu bekannten Buchungs-/PMS-Plattformen."""
    domain = _from_domain(from_address)
    return bool(domain) and any(known in domain for known in _TRUSTED_BOOKING_DOMAINS)


def has_text_booking_signals(email: EmailLike) -> bool:
    """Buchungs-Keywords in Betreff oder Body (ohne Extraktion)."""
    combined = f"{email.subject or ''}\n{email.body_text or ''}"
    return bool(_BOOKING_SIGNAL_RE.search(combined))


def has_reservation_request_signals(email: EmailLike) -> bool:
    """Freitext-Anfrage nach neuer Buchung / Reservierung."""
    combined = f"{email.subject or ''}\n{email.body_text or ''}"
    return bool(_RESERVATION_REQUEST_RE.search(combined))


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


def is_marketing_noise(email: EmailLike) -> bool:
    """Newsletter / interne Infos."""
    from_addr = (email.from_address or "").lower()
    subject = email.subject or ""
    for frag in _NOISE_SENDER_SUBSTRINGS:
        if frag in from_addr:
            return True
    for pattern in _NOISE_SUBJECT_PATTERNS:
        if pattern.search(subject):
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
