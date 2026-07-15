"""Auflösung der WhatsApp-Absendernummer → Mandant + Rolle."""

from __future__ import annotations

import logging

from backend.core.utils.phone import normalize_phone_digits
from backend.features.cleaning.models import CleaningPartner
from backend.features.whatsapp_bot.models import BotRole, ResolvedSender
from backend.infrastructure.repositories.cleaning_partner_repository import (
    CleaningPartnerRepository,
)
from backend.infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

# Dashboard-Rollen → Bot-Rollen. Platform-Admins agieren als Owner ihres
# eigenen Accounts; "member" darf verwalten, aber keine Mitarbeiter anlegen.
_USER_ROLE_MAP: dict[str, BotRole] = {
    "owner": "owner",
    "admin": "owner",
    "platform_admin": "owner",
    "member": "manager",
}


def normalize_wa_id(phone: str | None) -> str:
    """Nur Ziffern (Meta wa_id-Format, z. B. '4915712345678')."""
    return normalize_phone_digits(phone)


class SenderResolver:
    """wa_id → (account_id, Rolle). Unbekannte Nummern → None."""

    def __init__(
        self,
        user_repo: UserRepository,
        cleaning_partner_repo: CleaningPartnerRepository,
    ) -> None:
        """Initialize with repositories."""
        self._user_repo = user_repo
        self._partner_repo = cleaning_partner_repo

    def resolve(self, wa_id: str, *, account_id: str) -> ResolvedSender | None:
        """Sucht die Nummer bei Dashboard-Usern, dann bei Putzpartnern.

        Es wird ausschließlich innerhalb des per phone_number_id
        aufgelösten Accounts gesucht (Tenant-Isolation).
        """
        digits = normalize_wa_id(wa_id)
        if not digits:
            return None

        for user in self._user_repo.list_by_account_id(account_id):
            if normalize_wa_id(user.whatsapp_phone_e164) == digits:
                role = _USER_ROLE_MAP.get(user.role, "manager")
                name = (
                    f"{user.first_name or ''} {user.last_name or ''}".strip()
                    or user.email
                )
                return ResolvedSender(
                    account_id=account_id,
                    wa_id=digits,
                    name=name,
                    role=role,
                )

        partner = self._find_partner(digits, account_id)
        if partner is not None:
            return ResolvedSender(
                account_id=account_id,
                wa_id=digits,
                name=partner.name,
                role="cleaner",
                partner_id=partner.partner_id,
            )

        logger.info("WhatsApp-Bot: unbekannte Nummer für Account %s", account_id)
        return None

    def _find_partner(self, digits: str, account_id: str) -> CleaningPartner | None:
        for partner in self._partner_repo.list_partners(
            account_id=account_id, active_only=True
        ):
            if normalize_wa_id(partner.phone) == digits:
                return partner
        return None
