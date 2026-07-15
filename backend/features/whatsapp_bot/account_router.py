"""Mandanten-Routing für eingehende WhatsApp-Nachrichten.

Zwei Modelle laufen nebeneinander:

* **Dedizierte Nummer pro Mandant** – jeder Mandant hat seine eigene
  WhatsApp-Nummer; die Zuordnung erfolgt über die ``phone_number_id`` des
  Empfängers (klassisch, ``platform_settings.whatsapp_phone_number_id``).
* **Geteilte Plattform-Nummer** – alle Mandanten teilen sich EINE Nummer
  (die des Betreibers, ``WHATSAPP_PHONE_NUMBER_ID``). Dann wird der Mandant
  über die **Absendernummer** (``wa_id``) quer über alle Konten bestimmt.
  Voraussetzung: jede Absendernummer gehört nur EINEM Konto (sonst
  ``ambiguous`` statt falscher Zuordnung).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.core.utils.phone import normalize_phone_digits


@dataclass
class RoutingResult:
    """Ergebnis der Mandanten-Auflösung eines Webhook-Payloads."""

    account_id: str | None
    status: str  # resolved | no_account | unknown_sender | ambiguous | ignored


def extract_phone_number_id(payload: dict[str, Any]) -> str:
    """Liest die (Empfänger-)``phone_number_id`` aus dem Meta-Payload."""
    try:
        value = payload["entry"][0]["changes"][0]["value"]
        return str(value.get("metadata", {}).get("phone_number_id", "") or "")
    except (KeyError, IndexError, TypeError):
        return ""


def extract_sender_wa_id(payload: dict[str, Any]) -> str:
    """Liest die Absendernummer der ersten eingehenden Nachricht.

    Status-Webhooks (delivered/read) enthalten keine ``messages`` und liefern
    daher ``""`` – sie sollen nicht geroutet werden.
    """
    try:
        value = payload["entry"][0]["changes"][0]["value"]
    except (KeyError, IndexError, TypeError):
        return ""
    msgs = value.get("messages") or []
    if not msgs:
        return ""
    return str(msgs[0].get("from", "") or "")


class AccountRouter:
    """Ordnet einen eingehenden Webhook-Payload einem Mandanten zu."""

    def __init__(
        self,
        *,
        platform_settings_repo: Any,
        user_repo: Any,
        cleaning_partner_repo: Any,
        platform_phone_number_id: str,
    ) -> None:
        """Initialize with repositories and the shared platform number id."""
        self._platform_settings_repo = platform_settings_repo
        self._user_repo = user_repo
        self._partner_repo = cleaning_partner_repo
        self._platform_pnid = (platform_phone_number_id or "").strip()

    def route(self, payload: dict[str, Any]) -> RoutingResult:
        """Geteilte Plattform-Nummer → Absender-Routing, sonst über pnid."""
        pnid = extract_phone_number_id(payload)
        if self._platform_pnid and pnid == self._platform_pnid:
            return self._route_by_sender(payload)
        account_id = self._platform_settings_repo.find_account_by_phone_number_id(pnid)
        if account_id:
            return RoutingResult(account_id, "resolved")
        return RoutingResult(None, "no_account")

    def _route_by_sender(self, payload: dict[str, Any]) -> RoutingResult:
        digits = normalize_phone_digits(extract_sender_wa_id(payload))
        if not digits:
            return RoutingResult(None, "ignored")  # Status-Update ohne Absender
        accounts = set(self._user_repo.find_account_ids_by_whatsapp(digits))
        accounts |= set(self._partner_repo.find_account_ids_by_phone(digits))
        if len(accounts) == 1:
            return RoutingResult(next(iter(accounts)), "resolved")
        if not accounts:
            return RoutingResult(None, "unknown_sender")
        return RoutingResult(None, "ambiguous")
