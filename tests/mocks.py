"""Gemeinsame Test-Mocks."""

from __future__ import annotations

from services.llm_types import LLMCompletion


class MockLLM:
    """Mock für Klassifikation, Extraktion und Draft."""

    def complete(self, prompt: str, model: str) -> LLMCompletion:
        text = self._text_for(prompt)
        return LLMCompletion(text=text, prompt_tokens=10, completion_tokens=20)

    def _mail_section(self, prompt: str) -> str:
        """Nur den Mail-Block, nicht Few-Shots."""
        if "Mail:" in prompt:
            return prompt.rsplit("Mail:", 1)[-1]
        return prompt

    def _text_for(self, prompt: str) -> str:
        if "Antwortentwurf" in prompt or "Gast-Mail" in prompt:
            return "Sehr geehrte/r Gast, Ihre Anfrage wurde bearbeitet."
        if "Extrahiere strukturierte" in prompt:
            mail = self._mail_section(prompt)
            if "AB123" in mail:
                return (
                    '{"intent": "new_booking", "booking_number": "AB123", '
                    '"check_in": "2026-06-12", "check_out": "2026-06-15", '
                    '"guest_count": 2}'
                )
            if "AB200" in mail:
                return '{"intent": "cancellation", "booking_number": "AB200"}'
            if "XY999" in mail:
                return '{"intent": "cancellation", "booking_number": "XY999"}'
            if "PAY55" in mail:
                return '{"intent": "payment_issue", "booking_number": "PAY55"}'
            if "Bewertung" in mail or "Aufenthalt" in mail:
                return '{"intent": "review"}'
            if "stornieren" in mail.lower():
                return '{"intent": "cancellation", "booking_number": "XY999"}'
            return (
                '{"intent": "new_booking", "booking_number": "AB200", '
                '"check_in": "2026-06-12", "check_out": "2026-06-15"}'
            )
        mail = self._mail_section(prompt)
        if "Zahlung" in mail:
            return "payment_issue"
        if "Bewertung" in mail:
            return "review"
        if "Stornierung" in mail or "stornieren" in mail.lower():
            return "cancellation"
        if "Neue Buchung" in mail or "AB123" in mail:
            return "new_booking"
        if mail.strip().endswith("Inhalt:\n") or (
            "Inhalt:\n\n" in mail and len(mail.split("Inhalt:")[-1].strip()) < 3
        ):
            return "other"
        return "new_booking"
