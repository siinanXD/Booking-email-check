"""WhatsApp-Empfänger pro Unterkunft (Cleaner/Mitarbeiter)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from pymongo.collection import Collection

from repositories.mongo import Db


class PropertyWhatsAppRecipients(BaseModel):
    """Telefonnummern (E.164) für eine Unterkunft."""

    property_name: str
    phones: list[str] = Field(default_factory=list)


class PropertyRecipientRepository:
    """Collection `property_whatsapp_recipients`."""

    COLLECTION = "property_whatsapp_recipients"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]
        self._col.create_index("property_name", unique=True)

    def get_phones(self, property_name: str | None) -> list[str]:
        """Lädt Empfänger für eine Unterkunft (case-insensitive Match)."""
        if not property_name or not property_name.strip():
            return []
        key = property_name.strip().lower()
        doc = self._col.find_one({"property_name_lower": key})
        if doc is None:
            return []
        record = PropertyWhatsAppRecipients.model_validate(doc)
        return list(record.phones)

    def upsert(
        self, property_name: str, phones: list[str]
    ) -> PropertyWhatsAppRecipients:
        """Legt oder aktualisiert Empfänger für eine Unterkunft."""
        key = property_name.strip().lower()
        record = PropertyWhatsAppRecipients(
            property_name=property_name.strip(), phones=phones
        )
        doc = record.model_dump(mode="json")
        doc["_id"] = key
        doc["property_name_lower"] = key
        self._col.update_one({"_id": key}, {"$set": doc}, upsert=True)
        return record

    def list_all(self) -> list[PropertyWhatsAppRecipients]:
        """Alle Unterkunft → Telefon-Zuordnungen."""
        records: list[PropertyWhatsAppRecipients] = []
        for doc in self._col.find().sort("property_name", 1):
            payload = {
                k: v for k, v in doc.items() if k not in ("_id", "property_name_lower")
            }
            records.append(PropertyWhatsAppRecipients.model_validate(payload))
        return records

    def replace_all(self, items: list[tuple[str, list[str]]]) -> None:
        """Ersetzt die gesamte Empfänger-Liste (Settings-Speichern)."""
        self._col.delete_many({})
        for property_name, phones in items:
            name = property_name.strip()
            if not name:
                continue
            self.upsert(name, [p.strip() for p in phones if p.strip()])
