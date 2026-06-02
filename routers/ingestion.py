"""Ingestion-Schnittstelle (ohne HTTP im MVP)."""

from __future__ import annotations

from typing import Protocol

from models.email import IncomingEmail
from services.ingestion import IngestionService, IngestResult


class IngestionPort(Protocol):
    """Port für externe Ingestion-Adapter (Outlook, Webhook, …)."""

    def ingest_email(self, payload: IncomingEmail) -> IngestResult:
        """Eine Mail in die Pipeline aufnehmen."""
        ...


class IngestionRouter:
    """Standard-Implementierung des IngestionPort."""

    def __init__(self, service: IngestionService) -> None:
        self._service = service

    def ingest_email(self, payload: IncomingEmail) -> IngestResult:
        """Delegiert an den IngestionService."""
        return self._service.ingest(payload)
