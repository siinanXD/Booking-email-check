"""MongoDB-Verbindung."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Any, TypeAlias

from pymongo import MongoClient, monitoring
from pymongo.database import Database

if TYPE_CHECKING:
    from backend.core.config.settings import Settings

logger = logging.getLogger(__name__)

Db: TypeAlias = Database[dict[str, object]]

_SLOW_QUERY_THRESHOLD_MS = 100


class _SlowQueryLogger(monitoring.CommandListener):
    """Loggt MongoDB-Kommandos die das Schwellenlimit überschreiten."""

    def started(self, event: Any) -> None:  # noqa: ANN401
        pass

    def succeeded(self, event: Any) -> None:
        ms = event.duration_micros / 1000
        if ms > _SLOW_QUERY_THRESHOLD_MS:
            collection = ""
            command = getattr(event, "command", None)
            if isinstance(command, dict):
                collection = str(command.get(event.command_name, ""))
            logger.warning(
                "Slow MongoDB %s on %s: %.0fms (request_id=%s)",
                event.command_name,
                collection or "?",
                ms,
                event.request_id,
            )

    def failed(self, event: Any) -> None:
        logger.error(
            "MongoDB command failed: %s (request_id=%s, failure=%s)",
            event.command_name,
            event.request_id,
            event.failure,
        )


monitoring.register(_SlowQueryLogger())


@lru_cache(maxsize=4)
def _cached_client(mongodb_uri: str) -> MongoClient[dict[str, object]]:
    """Singleton MongoClient pro URI (Connection Pooling)."""
    return MongoClient(
        mongodb_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )


def get_client(settings: Settings) -> MongoClient[dict[str, object]]:
    """Gibt den gecachten MongoDB-Client für die Settings-URI zurück."""
    return _cached_client(settings.mongodb_uri)


def get_database(settings: Settings) -> Db:
    """Gibt die konfigurierte Datenbank zurück."""
    from backend.infrastructure.repositories.domain_collections import (
        ensure_domain_collections,
    )

    client = get_client(settings)
    db = client[settings.mongodb_db_name]
    ensure_domain_collections(db)
    return db


def ping(settings: Settings) -> bool:
    """Health-Check gegen den Cluster."""
    client = get_client(settings)
    client.admin.command("ping")
    return True
