"""IMAP-Server-Voreinstellungen für gängige Anbieter."""

from __future__ import annotations

from typing import TypedDict


class ImapPreset(TypedDict, total=False):
    label: str
    host: str
    port: int
    use_ssl: bool
    domains: list[str]


# Alle Einträge mit use_ssl=True und port=993 (IMAP over TLS).
IMAP_PRESETS: dict[str, ImapPreset] = {
    "gmx": {
        "label": "GMX",
        "host": "imap.gmx.net",
        "port": 993,
        "use_ssl": True,
        "domains": ["gmx.de", "gmx.net", "gmx.at", "gmx.ch", "gmx.com"],
    },
    "webde": {
        "label": "Web.de",
        "host": "imap.web.de",
        "port": 993,
        "use_ssl": True,
        "domains": ["web.de"],
    },
    "gmail": {
        "label": "Gmail",
        "host": "imap.gmail.com",
        "port": 993,
        "use_ssl": True,
        "domains": ["gmail.com", "googlemail.com"],
    },
    "tonline": {
        "label": "T-Online",
        "host": "secureimap.t-online.de",
        "port": 993,
        "use_ssl": True,
        "domains": ["t-online.de", "telekom.de", "magenta.de"],
    },
    "ionos": {
        "label": "1&1 / IONOS",
        "host": "imap.ionos.de",
        "port": 993,
        "use_ssl": True,
        "domains": [
            "ionos.de",
            "1und1.de",
            "1and1.com",
            "mail.com",
            "email.de",
            "usa.com",
            "myself.com",
            "cheerful.com",
            "hailmail.net",
            "iname.com",
            "inoutbox.com",
            "internetemails.net",
            "loveontario.com",
            "lycosmail.com",
            "mr-berlin.com",
            "imap.com",
        ],
    },
    "strato": {
        "label": "Strato",
        "host": "imap.strato.de",
        "port": 993,
        "use_ssl": True,
        "domains": ["strato.de", "strato-hosting.de"],
    },
    "posteo": {
        "label": "Posteo",
        "host": "posteo.de",
        "port": 993,
        "use_ssl": True,
        "domains": [
            "posteo.de",
            "posteo.at",
            "posteo.ch",
            "posteo.eu",
            "posteo.net",
            "posteo.org",
        ],
    },
    "mailboxorg": {
        "label": "mailbox.org",
        "host": "imap.mailbox.org",
        "port": 993,
        "use_ssl": True,
        "domains": ["mailbox.org"],
    },
    "freenet": {
        "label": "Freenet",
        "host": "mx.freenet.de",
        "port": 993,
        "use_ssl": True,
        "domains": ["freenet.de"],
    },
    "yahoo": {
        "label": "Yahoo Mail",
        "host": "imap.mail.yahoo.com",
        "port": 993,
        "use_ssl": True,
        "domains": [
            "yahoo.de",
            "yahoo.com",
            "yahoo.co.uk",
            "yahoo.fr",
            "yahoo.at",
            "yahoo.ch",
            "ymail.com",
            "rocketmail.com",
        ],
    },
    "aol": {
        "label": "AOL Mail",
        "host": "imap.aol.com",
        "port": 993,
        "use_ssl": True,
        "domains": [
            "aol.com",
            "aol.de",
            "aol.co.uk",
            "aol.at",
            "aol.com.au",
            "aim.com",
        ],
    },
    "icloud": {
        "label": "iCloud Mail",
        "host": "imap.mail.me.com",
        "port": 993,
        "use_ssl": True,
        "domains": ["icloud.com", "me.com", "mac.com"],
    },
    "zoho": {
        "label": "Zoho Mail",
        "host": "imap.zoho.eu",
        "port": 993,
        "use_ssl": True,
        "domains": ["zoho.com", "zoho.eu"],
    },
    "outlook_imap": {
        "label": "Outlook.com / Hotmail (IMAP)",
        "host": "outlook.office365.com",
        "port": 993,
        "use_ssl": True,
        "domains": [
            "outlook.com",
            "outlook.de",
            "outlook.at",
            "outlook.ch",
            "hotmail.com",
            "hotmail.de",
            "hotmail.co.uk",
            "hotmail.fr",
            "live.com",
            "live.de",
            "live.co.uk",
            "msn.com",
        ],
    },
    "office365": {
        "label": "Microsoft 365 (IMAP)",
        "host": "outlook.office365.com",
        "port": 993,
        "use_ssl": True,
        "domains": [],
    },
    "custom": {
        "label": "Eigener IMAP-Server",
        "host": "",
        "port": 993,
        "use_ssl": True,
        "domains": [],
    },
}

# Schnell-Lookup: Domain → Preset-ID
_DOMAIN_INDEX: dict[str, str] = {
    domain: preset_id
    for preset_id, preset in IMAP_PRESETS.items()
    for domain in preset.get("domains", [])
}


def find_preset_by_domain(domain: str) -> str | None:
    """Gibt die Preset-ID für eine E-Mail-Domain zurück, oder None."""
    return _DOMAIN_INDEX.get(domain.lower().strip())
