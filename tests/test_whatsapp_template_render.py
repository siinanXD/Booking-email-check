"""WhatsApp-Template-Rendering für Review."""

from __future__ import annotations

from backend.core.models.notification import NotificationKind
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


def test_render_status_body_always_german_shell() -> None:
    body = render_whatsapp_body(
        NotificationKind.BOOKING_STATUS_NOTICE,
        [
            "Storno",
            "Loft Nord",
            "01.07.2026",
            "05.07.2026",
            "Max Mustermann",
            "BK-9",
        ],
        "pl",
    )
    assert "Buchungsupdate: Storno" in body
    assert "Gast: Max Mustermann" in body
