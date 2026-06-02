"""Fachliche Entitäten der Booking-Domäne."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class Guest(BaseModel):
    """Gast-Entität."""

    guest_id: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    platform: str | None = None
    created_at: datetime | None = None

    def to_mongo(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> Guest:
        payload = {k: v for k, v in doc.items() if k != "_id"}
        if "_id" in doc:
            payload["guest_id"] = str(doc["_id"])
        return cls.model_validate(payload)


class Property(BaseModel):
    """Unterkunft."""

    property_id: str
    name: str
    platform: str | None = None

    def to_mongo(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> Property:
        payload = {k: v for k, v in doc.items() if k != "_id"}
        if "_id" in doc:
            payload["property_id"] = str(doc["_id"])
        return cls.model_validate(payload)


class Reservation(BaseModel):
    """Buchung / Reservierung."""

    reservation_id: str
    guest_id: str | None = None
    property_id: str | None = None
    booking_number: str | None = None
    check_in: date | None = None
    check_out: date | None = None
    guest_count: int | None = None
    price: float | None = None
    currency: str | None = None
    status: str | None = None
    platform: str | None = None
    correlation_id: str | None = None

    def to_mongo(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> Reservation:
        payload = {k: v for k, v in doc.items() if k != "_id"}
        if "_id" in doc:
            payload["reservation_id"] = str(doc["_id"])
        return cls.model_validate(payload)


class Message(BaseModel):
    """Verknüpfung einer Mail mit Entitäten."""

    message_id: str
    correlation_id: str
    guest_id: str | None = None
    reservation_id: str | None = None

    def to_mongo(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> Message:
        payload = {k: v for k, v in doc.items() if k != "_id"}
        return cls.model_validate(payload)
