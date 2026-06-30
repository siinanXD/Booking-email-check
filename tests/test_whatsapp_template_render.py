"""WhatsApp-Template-Rendering für Review."""

from __future__ import annotations

from backend.core.models.notification import NotificationKind
from backend.features.notifications.whatsapp_locale import localized_template_name
from backend.features.notifications.whatsapp_template_render import render_whatsapp_body


def test_render_cleaning_body_german() -> None:
    body = render_whatsapp_body(
        NotificationKind.BOOKING_CLEANING_TASK,
        ["Apartment Mitte", "10.06.2026", "15.06.2026", "Check-out Reinigung", "AB100"],
        "de",
    )
    assert "Neue Reinigungsaufgabe für dein Team" in body
    assert "Apartment Mitte" in body
    assert "Check-out Reinigung" in body


def test_render_cleaning_body_polish() -> None:
    body = render_whatsapp_body(
        NotificationKind.BOOKING_CLEANING_TASK,
        [
            "Apartment Mitte",
            "10.06.2026",
            "15.06.2026",
            "Sprzątanie po wymeldowaniu",
            "AB100",
        ],
        "pl",
    )
    assert "Masz nowe zlecenie sprzątania" in body
    assert "Sprzątanie po wymeldowaniu" in body


def _status_params() -> list[str]:
    return ["Storno", "Loft Nord", "01.07.2026", "05.07.2026", "Max Mustermann", "BK-9"]


def test_render_status_body_german() -> None:
    body = render_whatsapp_body(
        NotificationKind.BOOKING_STATUS_NOTICE, _status_params(), "de"
    )
    assert "Buchungsupdate: Storno" in body
    assert "Gast: Max Mustermann" in body


def test_render_status_body_polish() -> None:
    body = render_whatsapp_body(
        NotificationKind.BOOKING_STATUS_NOTICE, _status_params(), "pl"
    )
    assert "Aktualizacja rezerwacji: Storno" in body
    assert "Gość: Max Mustermann" in body


def test_render_inquiry_body_english() -> None:
    body = render_whatsapp_body(
        NotificationKind.BOOKING_GUEST_INQUIRY,
        ["Complaint", "Loft Nord", "BK-9", "01.07.2026", "05.07.2026", "Max"],
        "en",
    )
    assert body.startswith("Complaint")
    assert "Property: Loft Nord" in body
    assert "Guest: Max" in body


def test_localized_template_name_switches_suffix() -> None:
    assert (
        localized_template_name("booking_status_notice_de", "de")
        == "booking_status_notice_de"
    )
    assert (
        localized_template_name("booking_status_notice_de", "en")
        == "booking_status_notice_en"
    )
    assert (
        localized_template_name("booking_guest_inquiry_de", "pl")
        == "booking_guest_inquiry_pl"
    )
