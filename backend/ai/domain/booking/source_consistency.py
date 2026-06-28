"""Deterministische Konsistenzprüfung der Quell-Mail.

Erkennt Widersprüche *innerhalb* der beds24-Mail, die ein Parser nicht heilen
kann (sie stammen aus der Quelle, z. B. Kalender-Sync auf beds24-Seite). Statt
sie still zu loggen, werden sie als ``source_flags`` an den Review gehängt und
ggf. eskaliert — so landen genau diese Fälle vor einem Menschen.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.ai.domain.booking.beds24_fields import (
    channel_from_domains_in_text,
    channel_from_email,
    channel_from_line,
    expects_room,
    parse_room_number,
)
from backend.ai.domain.booking.extraction import BookingExtraction
from backend.core.models.email import StoredEmail


@dataclass
class SourceConflict:
    """Ein erkannter Quelldaten-Widerspruch."""

    code: str
    message: str
    escalate: bool


def detect_source_conflicts(
    email: StoredEmail, extraction: BookingExtraction
) -> list[SourceConflict]:
    """Findet Widersprüche in Betreff/Body/Kanal dieser Mail."""
    body = email.body_text or ""
    subject = email.subject or ""
    conflicts: list[SourceConflict] = []

    room_body = parse_room_number(body)
    room_subject = parse_room_number(subject)
    if room_body and room_subject and room_body != room_subject:
        conflicts.append(
            SourceConflict(
                "room_mismatch",
                f"Zimmer widersprüchlich: Betreff Nr. {room_subject} "
                f"vs. Mailtext Nr. {room_body} — Quelle prüfen.",
                escalate=True,
            )
        )
    elif (
        expects_room(extraction.property_name, subject)
        and not room_body
        and not room_subject
    ):
        conflicts.append(
            SourceConflict(
                "room_missing",
                "Zimmernummer fehlt bei Multi-Zimmer-Objekt — Quelle prüfen.",
                escalate=True,
            )
        )

    # Verlässlicher Kanal (Gast-Domain) vs. beds24-Kanalzeile. Bewusst nur die
    # explizite Kanalzeile (nicht der Unit-Name) — sonst würde "Rebenglück Air
    # BNB" bei echtem Booking-Kanal fälschlich flaggen.
    domain_channel = channel_from_email(
        extraction.email
    ) or channel_from_domains_in_text(body, subject)
    line_channel = channel_from_line(body, subject)
    if domain_channel and line_channel and domain_channel != line_channel:
        conflicts.append(
            SourceConflict(
                "channel_mismatch",
                f"Kanal widersprüchlich: Mail nennt {line_channel}, "
                f"Gast-Domain deutet auf {domain_channel}.",
                escalate=False,
            )
        )
    return conflicts
