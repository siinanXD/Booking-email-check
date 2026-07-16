"""Löscht Anwendungsdaten pro Mandant – Benutzer bleiben."""

from __future__ import annotations

import logging
from typing import Any

from pymongo.database import Database

from backend.infrastructure.observability.langfuse_wipe import LangfuseWipeService
from backend.infrastructure.repositories.cleaning_partner_repository import (
    CleaningPartnerRepository,
)
from backend.infrastructure.repositories.domain_collections import (
    BOOKINGS,
    CHUNKS,
    CONVERSATIONS,
    GUESTS,
    PROPERTIES,
)
from backend.infrastructure.repositories.email_repository import EmailRepository
from backend.infrastructure.repositories.embedding_repository import EmbeddingRepository
from backend.infrastructure.repositories.extraction_repository import (
    ExtractionRepository,
)
from backend.infrastructure.repositories.mail_metrics_repository import (
    MailMetricsRepository,
)
from backend.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRepository,
)
from backend.infrastructure.repositories.review_repository import ReviewRepository
from backend.infrastructure.repositories.subscription_repository import (
    SubscriptionRepository,
)

logger = logging.getLogger(__name__)

WIPE_COLLECTIONS = (
    EmailRepository.COLLECTION,
    ExtractionRepository.COLLECTION,
    EmbeddingRepository.COLLECTION,
    ReviewRepository.COLLECTION,
    MailMetricsRepository.COLLECTION,
    NotificationRepository.COLLECTION,
    # Mitarbeiter/Putzpartner: eine Quelle (`cleaning_partners`). Die alte
    # `property_whatsapp_recipients` bleibt bis zur Migration in der Liste,
    # damit ein Wipe keine Telefonnummern von Altbeständen zurücklässt.
    CleaningPartnerRepository.COLLECTION,
    "property_whatsapp_recipients",
    "cleaning_tasks",
    PlatformSettingsRepository.COLLECTION,
    SubscriptionRepository.COLLECTION,
    "mail_connections",
    GUESTS,
    BOOKINGS,
    PROPERTIES,
    CONVERSATIONS,
    CHUNKS,
)


class DataWipeService:
    """Entfernt Betriebsdaten eines Mandanten aus MongoDB und optional Langfuse-Traces.

    Langfuse-Löschung ist optional (DSGVO): wird nur ausgeführt wenn
    ``langfuse_wipe`` übergeben wird. Fehler beim Langfuse-Löschen brechen
    den Wipe nicht ab — Mongo-Daten sind bereits entfernt.
    """

    def __init__(
        self,
        db: Database[Any],
        langfuse_wipe: LangfuseWipeService | None = None,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._db = db
        self._langfuse_wipe = langfuse_wipe

    def wipe_account(self, account_id: str) -> dict[str, int]:
        """Löscht alle Betriebsdaten eines Accounts inkl. Langfuse-Traces.

        Args:
            account_id: ID des Mandanten dessen Daten entfernt werden sollen.

        Returns:
            Dict mit Collection-Namen und Anzahl gelöschter Dokumente.
            Enthält zusätzlich ``langfuse_traces`` wenn Langfuse aktiv.
        """
        # Correlation-IDs vor dem Löschen sammeln (für Langfuse)
        correlation_ids: list[str] = []
        if self._langfuse_wipe is not None:
            correlation_ids = [
                str(doc["_id"])
                for doc in self._db[EmailRepository.COLLECTION].find(
                    {"account_id": account_id}, {"_id": 1}
                )
            ]

        counts: dict[str, int] = {}
        for name in WIPE_COLLECTIONS:
            if name == PlatformSettingsRepository.COLLECTION:
                result = self._db[name].delete_many({"_id": account_id})
            else:
                result = self._db[name].delete_many({"account_id": account_id})
            counts[name] = int(result.deleted_count)

        # Langfuse-Traces löschen (DSGVO: nach Mongo-Wipe, kein Rollback)
        if self._langfuse_wipe is not None and correlation_ids:
            try:
                deleted = self._langfuse_wipe.delete_traces_for_sessions(
                    correlation_ids
                )
                counts["langfuse_traces"] = deleted
            except Exception as exc:
                logger.warning("Langfuse-Trace-Wipe fehlgeschlagen: %s", exc)
                counts["langfuse_traces"] = 0

        return counts

    def wipe_all(self) -> dict[str, int]:
        """Legacy: löscht alle Betriebsdaten global (nur Migration/Tests)."""
        counts: dict[str, int] = {}
        for name in WIPE_COLLECTIONS:
            result = self._db[name].delete_many({})
            counts[name] = int(result.deleted_count)
        return counts
