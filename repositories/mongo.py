"""MongoDB-Verbindung."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

from pymongo import MongoClient
from pymongo.database import Database

if TYPE_CHECKING:
    from config.settings import Settings

Db: TypeAlias = Database[dict[str, object]]


def get_client(settings: Settings) -> MongoClient[dict[str, object]]:
    """Erstellt einen MongoDB-Client aus den Settings."""
    return MongoClient(settings.mongodb_uri)


def get_database(settings: Settings) -> Db:
    """Gibt die konfigurierte Datenbank zurück."""
    client = get_client(settings)
    return client[settings.mongodb_db_name]


def ping(settings: Settings) -> bool:
    """Health-Check gegen den Cluster."""
    client = get_client(settings)
    client.admin.command("ping")
    return True
