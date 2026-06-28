"""Deterministische Feld-Extraktion aus beds24-Buchungsmails.

beds24-Mails sind strukturierte Templates: die Zimmernummer steht als eigene
Zeile direkt unter dem Objektnamen ("Zimmer Nr. 3"), der Kanal als Zeile
("Booking.com 5628649148") bzw. in der Gast-Mail-Domain (@guest.booking.com).

Wichtig: Beide Felder werden **aus genau dieser Mail** geparst — nie aus
Kalender, letzter Buchung oder Objektkatalog. Das verhindert die im Ticket
beobachtete Cross-Contamination (falsche Zimmernummer einer Fremdbuchung).
Den Kanal leiten wir bevorzugt aus der Gast-Mail-Domain ab, weil beds24 die
Kanalzeile selbst gelegentlich falsch befüllt (z. B. "AirBNB" statt Booking).
"""

from __future__ import annotations

import re

# "Zimmer Nr. 3", "Zimmer Nr.1", "Zimmer Nummer 2" — case-insensitive.
_ROOM_RE = re.compile(r"zimmer\s*(?:nr\.?|nummer)\s*(\d{1,4})", re.IGNORECASE)

# Objektnamen mit Zimmern (Multi-Zimmer-Objekt) → Zimmer wird erwartet.
_MULTI_ROOM_HINT = re.compile(r"ferienzimmer|\bzimmer\b", re.IGNORECASE)

# Gast-Mail-Domain → Kanal (verlässlichstes Signal).
_DOMAIN_CHANNEL: list[tuple[str, str]] = [
    ("guest.booking.com", "Booking.com"),
    ("booking.com", "Booking.com"),
    ("guest.airbnb.com", "Airbnb"),
    ("reply.airbnb.com", "Airbnb"),
    ("relay.airbnb.com", "Airbnb"),
    ("airbnb.com", "Airbnb"),
    ("guest.vrbo.com", "Vrbo"),
    ("vrbo.com", "Vrbo"),
    ("expediapartnercentral.com", "Expedia"),
    ("expedia.com", "Expedia"),
]

# Im Mail-Body explizit genannter Kanal (Fallback, nachrangig zur Domain).
_BODY_CHANNEL: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"booking\.com", re.IGNORECASE), "Booking.com"),
    (re.compile(r"airbnb", re.IGNORECASE), "Airbnb"),
    (re.compile(r"\bvrbo\b", re.IGNORECASE), "Vrbo"),
    (re.compile(r"expedia", re.IGNORECASE), "Expedia"),
]


def parse_room_number(*texts: str | None) -> str | None:
    """Erste Zimmernummer aus den übergebenen Texten (Body/Betreff dieser Mail)."""
    for text in texts:
        if not text:
            continue
        match = _ROOM_RE.search(text)
        if match:
            return match.group(1)
    return None


def expects_room(property_name: str | None, *texts: str | None) -> bool:
    """True, wenn der Kontext ein Multi-Zimmer-Objekt nahelegt (für fail-loud)."""
    haystack = " ".join(t for t in (property_name, *texts) if t)
    return bool(_MULTI_ROOM_HINT.search(haystack))


def detect_channel(guest_email: str | None, *texts: str | None) -> str | None:
    """Buchungskanal aus Gast-Mail-Domain (bevorzugt) oder Body-Kanalzeile.

    Niemals aus dem Unit-/Objektnamen — der trägt im Bestand teils irreführende
    Bezeichnungen (z. B. Unit "Rebenglück Air BNB" bei Kanal Booking.com).
    """
    domain = ((guest_email or "").rsplit("@", 1)[-1]).strip().lower()
    if domain:
        for needle, channel in _DOMAIN_CHANNEL:
            if domain.endswith(needle):
                return channel
    # Eindeutige OTA-Domain im Body (z. B. "@guest.booking.com") schlägt eine
    # evtl. falsche beds24-Kanalbezeichnung ("AirBNB") — Domains zuerst prüfen.
    blob = " ".join(t.lower() for t in texts if t)
    if blob:
        for needle, channel in _DOMAIN_CHANNEL:
            if needle in blob:
                return channel
        for pattern, channel in _BODY_CHANNEL:
            if pattern.search(blob):
                return channel
    return None
