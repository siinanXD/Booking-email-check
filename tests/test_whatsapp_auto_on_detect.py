"""Tests für WHATSAPP_AUTO_ON_DETECT."""

from __future__ import annotations

from datetime import date

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from tests.mocks import MockWhatsAppClient
from tests.test_whatsapp_notification import _notification_svc


def test_dispatch_on_detect_when_enabled(mock_db: object) -> None:
    client = MockWhatsAppClient()
    svc = _notification_svc(
        mock_db,
        client=client,
        WHATSAPP_AUTO_ON_DETECT=True,
    )
    ext = BookingExtraction(
        intent=BookingIntent.NEW_BOOKING,
        property_name="Chalet",
        booking_number="AB1",
        check_in=date(2026, 7, 1),
        check_out=date(2026, 7, 5),
    )
    records = svc.dispatch_on_detect_if_enabled(
        "corr-auto",
        ext,
        account_id="acc-1",
    )
    assert len(records) >= 1
    assert len(client.sent) >= 1


def test_dispatch_on_detect_skipped_when_disabled(mock_db: object) -> None:
    client = MockWhatsAppClient()
    svc = _notification_svc(
        mock_db,
        client=client,
        WHATSAPP_AUTO_ON_DETECT=False,
    )
    ext = BookingExtraction(intent=BookingIntent.NEW_BOOKING, booking_number="AB2")
    assert svc.dispatch_on_detect_if_enabled("corr-off", ext, account_id="acc-1") == []
    assert len(client.sent) == 0
