"""Klassifikations-Taxonomie Booking."""

from __future__ import annotations

from enum import StrEnum


class BookingIntent(StrEnum):
    """Intent-Typen für eingehende Buchungsmails."""

    NEW_BOOKING = "new_booking"
    CHANGE = "change"
    CANCELLATION = "cancellation"
    PAYMENT_ISSUE = "payment_issue"
    GUEST_INQUIRY = "guest_inquiry"
    COMPLAINT = "complaint"
    REVIEW = "review"
    OTHER = "other"
