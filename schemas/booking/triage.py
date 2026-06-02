"""Triage-Ergebnisse (vorgelagertes Gate)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class TriageOutcome(StrEnum):
    """Ergebnis der billigen Vorprüfung."""

    RELEVANT = "relevant"
    SPAM_PHISHING = "spam_phishing"
    UNKNOWN_DOMAIN = "unknown_domain"


class TriageResult(BaseModel):
    """Triage mit optionaler Domänen-Zuordnung."""

    outcome: TriageOutcome
    domain: str = Field(default="booking")
    reason: str = ""
