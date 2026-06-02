"""Regelbasierte Triage (MVP, ohne LLM)."""

from __future__ import annotations

import re

from models.email import IncomingEmail
from schemas.booking.triage import TriageOutcome, TriageResult

_BLOCKLIST_DOMAINS = frozenset(
    {
        "mailer-daemon",
        "noreply",
        "no-reply",
        "donotreply",
    }
)

_PHISHING_PATTERNS = [
    re.compile(r"verify\s+your\s+account", re.IGNORECASE),
    re.compile(r"click\s+here\s+immediately", re.IGNORECASE),
    re.compile(r"password\s+expir", re.IGNORECASE),
    re.compile(r"urgent\s+action\s+required", re.IGNORECASE),
]

_KNOWN_BOOKING_DOMAINS = frozenset(
    {
        "airbnb.com",
        "booking.com",
        "expedia.com",
        "vrbo.com",
        "guest.booking.com",
    }
)


def _domain_from_address(address: str) -> str:
    if "@" not in address:
        return ""
    return address.split("@")[-1].lower().strip()


class TriageService:
    """Billige Vorprüfung vor teuren LLM-Aufrufen."""

    def triage(self, email: IncomingEmail) -> TriageResult:
        """Klassifiziert relevant / spam / unbekannte Domäne."""
        body = (email.body_text or "").strip()
        from_domain = _domain_from_address(email.from_address)

        for blocked in _BLOCKLIST_DOMAINS:
            if blocked in from_domain:
                return TriageResult(
                    outcome=TriageOutcome.SPAM_PHISHING,
                    reason=f"blocklisted_sender:{blocked}",
                )

        if not body and not (email.subject or "").strip():
            return TriageResult(
                outcome=TriageOutcome.SPAM_PHISHING,
                reason="empty_body_and_subject",
            )

        combined = f"{email.subject}\n{body}"
        for pattern in _PHISHING_PATTERNS:
            if pattern.search(combined):
                return TriageResult(
                    outcome=TriageOutcome.SPAM_PHISHING,
                    reason="phishing_pattern",
                )

        if (
            from_domain
            and not any(known in from_domain for known in _KNOWN_BOOKING_DOMAINS)
            and email.platform is None
        ):
            return TriageResult(
                outcome=TriageOutcome.UNKNOWN_DOMAIN,
                reason=f"unknown_sender_domain:{from_domain}",
            )

        return TriageResult(outcome=TriageOutcome.RELEVANT, reason="ok")
