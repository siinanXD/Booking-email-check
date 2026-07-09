"""Sprachnachrichten → Text (Whisper), mockbar über Protocol."""

from __future__ import annotations

import io
import logging
from typing import Protocol

logger = logging.getLogger(__name__)

_MAX_AUDIO_BYTES = 16 * 1024 * 1024  # Meta-Limit für Audio-Nachrichten


class Transcriber(Protocol):
    """Interface für Audio-Transkription."""

    def transcribe(self, audio: bytes, *, mime_type: str) -> str | None:
        """Gibt den transkribierten Text zurück (None bei Fehler)."""
        ...


class WhisperTranscriber:
    """OpenAI Whisper (Audio bleibt Daten — Ergebnis geht in die Intent-Pipeline)."""

    def __init__(self, api_key: str, *, model: str = "whisper-1") -> None:
        """Initialize with OpenAI API key."""
        self._api_key = api_key
        self._model = model

    def transcribe(self, audio: bytes, *, mime_type: str) -> str | None:
        """Transkribiert eine Sprachnachricht."""
        if not audio or len(audio) > _MAX_AUDIO_BYTES:
            return None
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._api_key)
            extension = _extension_for(mime_type)
            buffer = io.BytesIO(audio)
            result = client.audio.transcriptions.create(
                model=self._model,
                file=(f"voice{extension}", buffer, mime_type),
            )
            text = getattr(result, "text", "") or ""
            return text.strip() or None
        except Exception:
            logger.exception("Whisper-Transkription fehlgeschlagen")
            return None


def _extension_for(mime_type: str) -> str:
    mapping = {
        "audio/ogg": ".ogg",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/amr": ".amr",
        "audio/aac": ".aac",
    }
    base = mime_type.split(";")[0].strip().lower()
    return mapping.get(base, ".ogg")
