"""CRUD für Gäste und Reservierungen."""

from __future__ import annotations

from typing import Any

from pymongo.collection import Collection

from models.entities import Guest, Reservation
from repositories.mongo import Db


class EntityRepository:
    """Skeleton-Repository für Booking-Entitäten."""

    GUESTS = "guests"
    RESERVATIONS = "reservations"

    def __init__(self, db: Db) -> None:
        self._guests: Collection[dict[str, Any]] = db[self.GUESTS]
        self._reservations: Collection[dict[str, Any]] = db[self.RESERVATIONS]

    def upsert_guest(self, guest: Guest) -> Guest:
        """Gast speichern oder aktualisieren."""
        doc = guest.to_mongo()
        self._guests.update_one(
            {"_id": guest.guest_id},
            {"$set": doc},
            upsert=True,
        )
        return guest

    def get_guest_by_email(self, email: str) -> Guest | None:
        """Gast anhand E-Mail-Adresse."""
        doc = self._guests.find_one({"email": email})
        if doc is None:
            return None
        return Guest.from_mongo(doc)

    def upsert_reservation(self, reservation: Reservation) -> Reservation:
        """Reservierung speichern oder aktualisieren."""
        doc = reservation.to_mongo()
        self._reservations.update_one(
            {"_id": reservation.reservation_id},
            {"$set": doc},
            upsert=True,
        )
        return reservation

    def find_reservations_by_guest_email(self, email: str) -> list[Reservation]:
        """Reservierungen über Gast-E-Mail (über guest_id-Verknüpfung)."""
        guest = self.get_guest_by_email(email)
        if guest is None:
            return []
        cursor = self._reservations.find({"guest_id": guest.guest_id})
        return [Reservation.from_mongo(doc) for doc in cursor]

    def find_reservation_by_booking_number(
        self,
        booking_number: str,
    ) -> Reservation | None:
        """Reservierung anhand Buchungsnummer."""
        doc = self._reservations.find_one({"booking_number": booking_number})
        if doc is None:
            return None
        return Reservation.from_mongo(doc)

    def find_reservations_by_correlation_id(
        self,
        correlation_id: str,
    ) -> list[Reservation]:
        """Reservierungen einer Mail-Korrelation."""
        cursor = self._reservations.find({"correlation_id": correlation_id})
        return [Reservation.from_mongo(doc) for doc in cursor]
