"""MongoDB-Verbindung."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, TypeAlias

from pymongo import MongoClient
from pymongo.database import Database

if TYPE_CHECKING:
    from backend.core.config.settings import Settings

Db: TypeAlias = Database[dict[str, object]]


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
    client = get_client(settings)
    return client[settings.mongodb_db_name]


def ping(settings: Settings) -> bool:
    """Health-Check gegen den Cluster."""
    client = get_client(settings)
    client.admin.command("ping")
    return True
