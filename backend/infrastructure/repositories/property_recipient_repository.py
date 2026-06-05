"""WhatsApp-Empfänger pro Unterkunft (Cleaner/Mitarbeiter)."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator
from pymongo.collection import Collection

from backend.features.notifications.whatsapp_locale import (
    DEFAULT_EMPLOYEE_LOCALE,
    normalize_employee_locale,
)
from backend.infrastructure.repositories.mongo import Db

_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")


class PropertyWhatsAppEmployee(BaseModel):
    """Mitarbeiter-Empfänger mit bevorzugter WhatsApp-Sprache."""

    phone_e164: str
    locale: str = DEFAULT_EMPLOYEE_LOCALE

    @field_validator("phone_e164")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        phone = value.strip()
        if not _E164_RE.match(phone):
            msg = "phone_e164 muss E.164 sein (z. B. +491701234567)"
            raise ValueError(msg)
        return phone

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, value: str) -> str:
        return normalize_employee_locale(value)


class PropertyWhatsAppRecipients(BaseModel):
    """Mitarbeiter-Telefonnummern (E.164) für eine Unterkunft."""

    property_name: str
    employees: list[PropertyWhatsAppEmployee] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_phones(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("employees"):
            return data
        phones = data.get("phones") or []
        if not phones:
            return data
        payload = dict(data)
        payload["employees"] = [
            {"phone_e164": phone, "locale": DEFAULT_EMPLOYEE_LOCALE}
            for phone in phones
            if isinstance(phone, str) and phone.strip()
        ]
        return payload

    @property
    def phones(self) -> list[str]:
        return [employee.phone_e164 for employee in self.employees]


class PropertyRecipientRepository:
    """Collection `property_whatsapp_recipients`."""

    COLLECTION = "property_whatsapp_recipients"

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._col: Collection[dict[str, Any]] = db[self.COLLECTION]

    @staticmethod
    def _doc_id(account_id: str, property_name: str) -> str:
        key = property_name.strip().lower()
        return f"{account_id}:{key}"

    def get_phones(
        self,
        property_name: str | None,
        *,
        account_id: str | None = None,
    ) -> list[str]:
        """Lädt Telefonnummern für eine Unterkunft (case-insensitive Match)."""
        return [
            employee.phone_e164
            for employee in self.get_employees(property_name, account_id=account_id)
        ]

    def get_employees(
        self,
        property_name: str | None,
        *,
        account_id: str | None = None,
    ) -> list[PropertyWhatsAppEmployee]:
        """Lädt Mitarbeiter-Empfänger inkl. Sprache."""
        if not property_name or not property_name.strip() or not account_id:
            return []
        doc_id = self._doc_id(account_id, property_name)
        doc = self._col.find_one({"_id": doc_id})
        if doc is None:
            key = property_name.strip().lower()
            doc = self._col.find_one(
                {"property_name_lower": key, "account_id": account_id}
            )
        if doc is None:
            return []
        record = PropertyWhatsAppRecipients.model_validate(doc)
        return list(record.employees)

    def upsert(
        self,
        account_id: str,
        property_name: str,
        employees: list[PropertyWhatsAppEmployee] | list[str],
    ) -> PropertyWhatsAppRecipients:
        """Legt oder aktualisiert Empfänger für eine Unterkunft."""
        normalized = _normalize_employees(employees)
        key = property_name.strip().lower()
        record = PropertyWhatsAppRecipients(
            property_name=property_name.strip(),
            employees=normalized,
        )
        doc = record.model_dump(mode="json")
        doc["_id"] = self._doc_id(account_id, property_name)
        doc["account_id"] = account_id
        doc["property_name_lower"] = key
        self._col.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
        return record

    def list_all(self, account_id: str) -> list[PropertyWhatsAppRecipients]:
        """Alle Unterkunft → Telefon-Zuordnungen eines Accounts."""
        records: list[PropertyWhatsAppRecipients] = []
        cursor = self._col.find({"account_id": account_id}).sort("property_name", 1)
        for doc in cursor:
            payload = {
                k: v for k, v in doc.items() if k not in ("_id", "property_name_lower")
            }
            records.append(PropertyWhatsAppRecipients.model_validate(payload))
        return records

    def replace_all(
        self,
        account_id: str,
        items: list[tuple[str, list[PropertyWhatsAppEmployee]]],
    ) -> None:
        """Ersetzt die gesamte Empfänger-Liste eines Accounts."""
        self._col.delete_many({"account_id": account_id})
        for property_name, employees in items:
            name = property_name.strip()
            if not name:
                continue
            self.upsert(account_id, name, employees)


def _normalize_employees(
    employees: list[PropertyWhatsAppEmployee] | list[str],
) -> list[PropertyWhatsAppEmployee]:
    result: list[PropertyWhatsAppEmployee] = []
    for entry in employees:
        if isinstance(entry, PropertyWhatsAppEmployee):
            result.append(entry)
            continue
        phone = entry.strip()
        if phone:
            result.append(
                PropertyWhatsAppEmployee(
                    phone_e164=phone,
                    locale=DEFAULT_EMPLOYEE_LOCALE,
                )
            )
    return result
