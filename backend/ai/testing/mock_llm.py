"""LLM/Embedding-Mocks für Tests und LLM_MODE=mock (ohne OpenAI)."""

from __future__ import annotations

from backend.ai.services.llm_types import LLMCompletion


class MockLLM:
    """Mock für Klassifikation, Extraktion und Draft."""

    def complete(
        self,
        prompt: str,
        model: str,
        *,
        temperature: float | None = None,
    ) -> LLMCompletion:
        """Return a deterministic completion for the supplied test prompt."""
        _ = temperature
        text = self._text_for(prompt)
        return LLMCompletion(text=text, prompt_tokens=10, completion_tokens=20)

    def _mail_section(self, prompt: str) -> str:
        """Nur den Mail-Block, nicht Few-Shots."""
        start = "--- BEGIN UNTRUSTED MAIL ---"
        end = "--- END UNTRUSTED MAIL ---"
        if start in prompt and end in prompt:
            return prompt.rsplit(start, 1)[-1].split(end, 1)[0]
        if "Mail:" in prompt:
            return prompt.rsplit("Mail:", 1)[-1]
        return prompt

    def _text_for(self, prompt: str) -> str:
        """Choose a stable response based on the isolated mail body."""
        if "Du triagierst eingehende Mails" in prompt:
            mail = self._mail_section(prompt)
            if "Generic inquiry" in mail or "Hello" in mail:
                return "spam_phishing"
            if "appointment" in mail.lower() or "weird-startup" in mail:
                return "relevant"
            if "Reservierung" in mail or "Buchung" in mail:
                return "relevant"
            return "spam_phishing"
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
            if "CHG88" in mail:
                return (
                    '{"intent": "change", "booking_number": "CHG88", '
                    '"check_in": "2026-06-20"}'
                )
            if "AB456" in mail:
                return '{"intent": "guest_inquiry", "booking_number": "AB456"}'
            if "CMP77" in mail:
                return (
                    '{"intent": "complaint", "booking_number": "CMP77", '
                    '"guest_name": "Thomas Weber"}'
                )
            if "DIR50" in mail:
                return (
                    '{"intent": "new_booking", "booking_number": "DIR50", '
                    '"check_in": "2026-08-01", "check_out": "2026-08-05", '
                    '"guest_count": 2}'
                )
            if "einchecken" in mail.lower() or "Parkplätze" in mail:
                return '{"intent": "guest_inquiry"}'
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
        if mail.strip().endswith("Inhalt:\n") or (
            "Inhalt:\n\n" in mail and len(mail.split("Inhalt:")[-1].strip()) < 3
        ):
            return "other"
        if "Änderung" in mail or "CHG88" in mail:
            return "change"
        if (
            "Frage" in mail
            or "einchecken" in mail.lower()
            or "Parkplätze" in mail
            or "relay.airbnb.com" in mail
        ):
            return "guest_inquiry"
        if "Stornierung" in mail or "stornieren" in mail.lower():
            return "cancellation"
        if "Beschwerde" in mail or "CMP77" in mail:
            return "complaint"
        if "Direktbuchung" in mail or "DIR50" in mail:
            return "new_booking"
        if "Neue Buchung" in mail or "AB123" in mail:
            return "new_booking"
        if "match oder other" in prompt.lower() or "slug: match" in prompt.lower():
            if any(k in mail.lower() for k in ("bestellung", "order", "ord-", "kauf")):
                return "match"
            return "other"
        return "new_booking"


class MockEmbeddingClient:
    """Embeddings ohne OpenAI (feste Vektoren)."""

    def embed(self, text: str) -> list[float]:
        """Return a fixed embedding vector without calling OpenAI."""
        _ = text
        return [1.0, 0.5, 0.25]
