"""PaddleOCR-basierte Texterkennung aus Bildern (optionale Abhängigkeit)."""

from __future__ import annotations

import io
import logging
from typing import Any

from backend.core.models.workflow_media import MediaPart

logger = logging.getLogger(__name__)

try:
    import paddleocr as _paddleocr_mod

    _PADDLE_AVAILABLE = True
except ImportError:
    _PADDLE_AVAILABLE = False
    _paddleocr_mod = None

_ocr_instance: Any = None


def ocr_available() -> bool:
    """True wenn PaddleOCR installiert ist."""
    return _PADDLE_AVAILABLE


def _get_ocr() -> Any:
    global _ocr_instance
    if _ocr_instance is None:
        if not _PADDLE_AVAILABLE or _paddleocr_mod is None:
            raise RuntimeError("PaddleOCR nicht verfügbar")
        _ocr_instance = _paddleocr_mod.PaddleOCR(
            use_angle_cls=True,
            lang="en",
            show_log=False,
        )
    return _ocr_instance


def extract_text_from_bytes(data: bytes) -> str:
    """Extrahiert Text aus Bildbytes via PaddleOCR.

    Gibt leeren String zurück wenn kein Text erkannt oder Fehler auftritt.
    """
    if not _PADDLE_AVAILABLE:
        raise RuntimeError(
            "PaddleOCR ist nicht installiert. "
            "Installieren mit: pip install 'email-platform[ocr]'"
        )
    try:
        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(data)).convert("RGB")
        arr = np.array(img)
        ocr = _get_ocr()
        result: Any = ocr.ocr(arr, cls=True)
        lines: list[str] = []
        for block in result or []:
            for line in block or []:
                if isinstance(line, list | tuple) and len(line) >= 2:
                    text_conf = line[1]
                    if isinstance(text_conf, list | tuple) and text_conf:
                        text = str(text_conf[0]).strip()
                        if text:
                            lines.append(text)
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("OCR-Texterkennung fehlgeschlagen: %s", exc)
        return ""


def extract_text_from_parts(parts: list[MediaPart]) -> str:
    """Extrahiert und kombiniert OCR-Text aus Bild-MediaParts."""
    results: list[str] = []
    for part in parts:
        if not part.mime_type.startswith("image/"):
            continue
        text = extract_text_from_bytes(part.data)
        if text.strip():
            label = part.filename or part.mime_type
            results.append(f"[{label}]\n{text}")
    return "\n\n---\n\n".join(results)
