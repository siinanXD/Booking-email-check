"""Factory für Gemini-Clients (live / mock)."""

from __future__ import annotations

from backend.ai.services.gemini_client import GeminiClient, GeminiClientProtocol
from backend.ai.services.gemini_setup import gemini_configured
from backend.ai.testing.mock_gemini import MockGemini
from backend.core.config.settings import Settings


def build_gemini_client(settings: Settings) -> GeminiClientProtocol | None:
    """Erzeugt Gemini-Client oder None wenn weder Key noch mock."""
    mode = settings.llm_mode.strip().lower()
    if mode == "mock":
        return MockGemini()
    if gemini_configured(settings):
        return GeminiClient(settings.gemini_api_key.strip())
    return None
