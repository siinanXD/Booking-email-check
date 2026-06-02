"""Löscht Anwendungsdaten (E-Mails, Reviews, Einstellungen) – Benutzer bleiben."""

from __future__ import annotations

from typing import Any

from pymongo.database import Database

from repositories.email_repository import EmailRepository
from repositories.embedding_repository import EmbeddingRepository
from repositories.extraction_repository import ExtractionRepository
from repositories.mail_metrics_repository import MailMetricsRepository
from repositories.notification_repository import NotificationRepository
from repositories.platform_settings_repository import PlatformSettingsRepository
from repositories.property_recipient_repository import PropertyRecipientRepository
from repositories.review_repository import ReviewRepository

WIPE_COLLECTIONS = (
    EmailRepository.COLLECTION,
    ExtractionRepository.COLLECTION,
    EmbeddingRepository.COLLECTION,
    ReviewRepository.COLLECTION,
    MailMetricsRepository.COLLECTION,
    NotificationRepository.COLLECTION,
    PropertyRecipientRepository.COLLECTION,
    PlatformSettingsRepository.COLLECTION,
    "entities",
)


class DataWipeService:
    """Entfernt alle Betriebsdaten aus MongoDB."""

    def __init__(self, db: Database[Any]) -> None:
        """Initialize the instance with its dependencies."""
        self._db = db

    def wipe_all(self) -> dict[str, int]:
        """Löscht alle relevanten Collections; gibt gelöschte Dokumentzahlen zurück."""
        counts: dict[str, int] = {}
        for name in WIPE_COLLECTIONS:
            result = self._db[name].delete_many({})
            counts[name] = int(result.deleted_count)
        return counts
