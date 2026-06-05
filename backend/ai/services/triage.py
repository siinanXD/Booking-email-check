"""Regelbasierte Triage mit optionalem LLM-Gate für unbekannte Domains."""

from __future__ import annotations

import re

from backend.ai.domain.booking.booking_relevance import (
    _TRUSTED_BOOKING_DOMAINS,
    has_text_booking_signals,
    is_marketing_noise,
    is_probable_booking_mail,
    is_probable_non_booking_mail,
)
from backend.ai.domain.booking.triage import TriageOutcome, TriageResult
from backend.ai.services.classification import LLMClient
from backend.ai.services.triage_llm import TriageLlmService
from backend.core.models.email import IncomingEmail
from backend.infrastructure.observability.alerts import AlertService
from backend.infrastructure.observability.mail_cost import MailCostTracker

_BLOCKLIST_DOMAINS = frozenset(
    {
        "mailer-daemon",
        "noreply",
        "no-reply",
        "donotreply",
        "comigo",
        "lumigita",
        "lomigata",
    }
)

_PHISHING_PATTERNS = [
    re.compile(r"verify\s+your\s+account", re.IGNORECASE),
    re.compile(r"click\s+here\s+immediately", re.IGNORECASE),
    re.compile(r"password\s+expir", re.IGNORECASE),
    re.compile(r"urgent\s+action\s+required", re.IGNORECASE),
]


def _domain_from_address(address: str) -> str:
    if "@" not in address:
        return ""
    return address.split("@")[-1].lower().strip()


def _is_unknown_domain_candidate(from_address: str) -> bool:
    domain = _domain_from_address(from_address)
    if not domain:
        return True
    return not any(known in domain for known in _TRUSTED_BOOKING_DOMAINS)


class TriageService:
    """Billige Vorprüfung vor teuren LLM-Aufrufen (classify/extract)."""

    def __init__(
        self,
        *,
        llm: LLMClient | None = None,
        model: str = "gpt-4o-mini",
        triage_llm_enabled: bool = True,
        max_body_chars: int = 2000,
        tracing: bool = False,
        alerts: AlertService | None = None,
        mail_cost: MailCostTracker | None = None,
    ) -> None:
        self._triage_llm: TriageLlmService | None = None
        if llm is not None and triage_llm_enabled:
            self._triage_llm = TriageLlmService(
                llm,
                model,
                max_body_chars=max_body_chars,
                tracing=tracing,
                alerts=alerts,
                mail_cost=mail_cost,
            )

    def triage(self, email: IncomingEmail) -> TriageResult:
        """Klassifiziert relevant / spam; UNKNOWN_DOMAIN nur intern vor LLM-Gate."""
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

        if is_marketing_noise(email):
            return TriageResult(
                outcome=TriageOutcome.SPAM_PHISHING,
                reason="marketing_noise",
            )

        if is_probable_non_booking_mail(email):
            return TriageResult(
                outcome=TriageOutcome.SPAM_PHISHING,
                reason="non_booking_mail",
            )

        if is_probable_booking_mail(email):
            return TriageResult(
                outcome=TriageOutcome.RELEVANT,
                reason="booking_heuristic",
            )

        combined = f"{email.subject}\n{body}"
        for pattern in _PHISHING_PATTERNS:
            if pattern.search(combined):
                return TriageResult(
                    outcome=TriageOutcome.SPAM_PHISHING,
                    reason="phishing_pattern",
                )

        if _is_unknown_domain_candidate(email.from_address):
            return self._resolve_unknown_domain(email)

        return TriageResult(outcome=TriageOutcome.RELEVANT, reason="ok")

    def _resolve_unknown_domain(self, email: IncomingEmail) -> TriageResult:
        if self._triage_llm is not None:
            return self._triage_llm.triage_unknown_domain(email)
        if has_text_booking_signals(email):
            return TriageResult(
                outcome=TriageOutcome.RELEVANT,
                reason="unknown_domain_with_signals",
            )
        return TriageResult(
            outcome=TriageOutcome.SPAM_PHISHING,
            reason="unknown_domain_no_signals",
        )
