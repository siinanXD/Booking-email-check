"""WhatsApp-Empfänger pro Unterkunft — abgeleitete Sicht auf `cleaning_partners`.

Mitarbeiter lagen früher doppelt vor: der Bot schrieb nach `cleaning_partners`,
die Weboberfläche las `property_whatsapp_recipients`. Die Töpfe liefen auseinander
— per Chat angelegte Mitarbeiter tauchten im Web nie auf. `cleaning_partners` ist
darum die einzige Quelle; hier liegt nur die objekt-zentrische Sicht darauf
(Objekt → Empfänger), während `CleaningPartner` partner-zentrisch bleibt
(Partner → Objekte). Die Schnittstelle bleibt, damit Aufrufer nichts merken.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.features.cleaning.identity import cleaning_partner_id
from backend.features.cleaning.models import CleaningPartner
from backend.features.notifications.whatsapp_locale import (
    DEFAULT_EMPLOYEE_LOCALE,
    normalize_employee_locale,
)
from backend.infrastructure.repositories.cleaning_partner_repository import (
    CleaningPartnerRepository,
)
from backend.infrastructure.repositories.mongo import Db

_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")


class PropertyWhatsAppEmployee(BaseModel):
    """Mitarbeiter-Empfänger mit bevorzugter WhatsApp-Sprache."""

    phone_e164: str
    locale: str = DEFAULT_EMPLOYEE_LOCALE

    @field_validator("phone_e164")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        phone = value.strip()
        if not _E164_RE.match(phone):
            msg = "phone_e164 muss E.164 sein (z. B. +491701234567)"
            raise ValueError(msg)
        return phone

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, value: str) -> str:
        return normalize_employee_locale(value)


class PropertyWhatsAppRecipients(BaseModel):
    """Mitarbeiter-Telefonnummern (E.164) für eine Unterkunft."""

    property_name: str
    employees: list[PropertyWhatsAppEmployee] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_phones(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("employees"):
            return data
        phones = data.get("phones") or []
        if not phones:
            return data
        payload = dict(data)
        payload["employees"] = [
            {"phone_e164": phone, "locale": DEFAULT_EMPLOYEE_LOCALE}
            for phone in phones
            if isinstance(phone, str) and phone.strip()
        ]
        return payload

    @property
    def phones(self) -> list[str]:
        return [employee.phone_e164 for employee in self.employees]


class PropertyRecipientRepository:
    """Objekt-zentrische Sicht auf `cleaning_partners` (keine eigene Collection)."""

    def __init__(self, db: Db) -> None:
        """Initialize the instance with its dependencies."""
        self._partners = CleaningPartnerRepository(db)

    def get_phones(
        self,
        property_name: str | None,
        *,
        account_id: str | None = None,
        include_test_mode: bool = False,
    ) -> list[str]:
        """Lädt Telefonnummern für eine Unterkunft (case-insensitive Match)."""
        return [
            employee.phone_e164
            for employee in self.get_employees(
                property_name,
                account_id=account_id,
                include_test_mode=include_test_mode,
            )
        ]

    def get_employees(
        self,
        property_name: str | None,
        *,
        account_id: str | None = None,
        include_test_mode: bool = False,
    ) -> list[PropertyWhatsAppEmployee]:
        """Lädt Mitarbeiter-Empfänger inkl. Sprache.

        Testmodus-Partner bleiben standardmäßig draußen: Aufrufer dieser Methode
        versenden echte Nachrichten. Die Weboberfläche setzt ``include_test_mode``,
        weil sie den Partner anzeigen, aber nichts senden will.
        """
        if not property_name or not property_name.strip() or not account_id:
            return []
        partners = self._partners.find_for_property(
            property_name, account_id=account_id
        )
        return _to_employees(partners, include_test_mode=include_test_mode)

    def list_all(
        self,
        account_id: str,
        *,
        include_test_mode: bool = False,
    ) -> list[PropertyWhatsAppRecipients]:
        """Alle Unterkunft → Empfänger-Zuordnungen eines Accounts."""
        by_property: dict[str, list[CleaningPartner]] = {}
        for partner in self._partners.list_partners(
            account_id=account_id, active_only=True
        ):
            for name in partner.property_names:
                key = name.strip()
                if key:
                    by_property.setdefault(key, []).append(partner)
        return [
            PropertyWhatsAppRecipients(
                property_name=name,
                employees=_to_employees(partners, include_test_mode=include_test_mode),
            )
            for name, partners in sorted(
                by_property.items(), key=lambda x: x[0].lower()
            )
        ]

    def upsert(
        self,
        account_id: str,
        property_name: str,
        employees: list[PropertyWhatsAppEmployee] | list[str],
    ) -> PropertyWhatsAppRecipients:
        """Setzt die Empfänger einer Unterkunft (legt Partner an bzw. löst sie ab).

        Reconcile statt Überschreiben: bestehende Partner behalten Name, Adresse
        und Testmodus — nur die Objektzuordnung und die Sprache werden gepflegt.
        """
        name = property_name.strip()
        normalized = _normalize_employees(employees)
        if not name:
            return PropertyWhatsAppRecipients(property_name=name, employees=normalized)

        wanted = {e.phone_e164: e for e in normalized}
        for partner in self._partners.find_for_property(name, account_id=account_id):
            phone = (partner.phone or "").strip()
            if phone in wanted:
                # Bleibt zugeordnet — nur die Sprache nachziehen.
                partner.locale = wanted[phone].locale
                _attach(partner, name)
                self._partners.upsert(partner, account_id=account_id)
                wanted.pop(phone)
            else:
                _detach(partner, name)
                self._partners.upsert(partner, account_id=account_id)

        for employee in wanted.values():
            self._partners.upsert(
                _new_partner(account_id, name, employee),
                account_id=account_id,
            )
        return PropertyWhatsAppRecipients(property_name=name, employees=normalized)

    def replace_all(
        self,
        account_id: str,
        items: list[tuple[str, list[PropertyWhatsAppEmployee]]],
    ) -> None:
        """Ersetzt die gesamte Empfänger-Liste eines Accounts."""
        seen: set[str] = set()
        for property_name, employees in items:
            name = property_name.strip()
            if not name:
                continue
            self.upsert(account_id, name, employees)
            seen.add(name.strip().lower())
        # Objekte, die nicht mehr vorkommen, von allen Partnern lösen.
        for partner in self._partners.list_partners(account_id=account_id):
            remaining = [n for n in partner.property_names if n.strip().lower() in seen]
            if len(remaining) != len(partner.property_names):
                partner.property_names = remaining
                self._partners.upsert(partner, account_id=account_id)

    def rename_property(self, account_id: str, old_name: str, new_name: str) -> None:
        """Zieht eine Objekt-Umbenennung durch alle Partner nach.

        Ohne das verwaisen die Zuordnungen still — der Partner bleibt auf dem
        alten Namen stehen und bekommt für das umbenannte Objekt nichts mehr.
        """
        old, new = old_name.strip(), new_name.strip()
        if not old or not new or old.lower() == new.lower():
            return
        for partner in self._partners.find_for_property(old, account_id=account_id):
            _detach(partner, old)
            _attach(partner, new)
            self._partners.upsert(partner, account_id=account_id)


def _to_employees(
    partners: list[CleaningPartner],
    *,
    include_test_mode: bool,
) -> list[PropertyWhatsAppEmployee]:
    """Partner → Empfänger, dedupliziert nach Telefonnummer."""
    result: list[PropertyWhatsAppEmployee] = []
    seen: set[str] = set()
    for partner in partners:
        phone = (partner.phone or "").strip()
        if not phone or phone in seen:
            continue
        if partner.test_mode and not include_test_mode:
            continue
        if not _E164_RE.match(phone):
            continue
        seen.add(phone)
        result.append(
            PropertyWhatsAppEmployee(
                phone_e164=phone,
                locale=normalize_employee_locale(partner.locale),
            )
        )
    return result


def _attach(partner: CleaningPartner, name: str) -> None:
    if name.strip().lower() not in {n.strip().lower() for n in partner.property_names}:
        partner.property_names = [*partner.property_names, name.strip()]


def _detach(partner: CleaningPartner, name: str) -> None:
    key = name.strip().lower()
    partner.property_names = [
        n for n in partner.property_names if n.strip().lower() != key
    ]


def _new_partner(
    account_id: str,
    property_name: str,
    employee: PropertyWhatsAppEmployee,
) -> CleaningPartner:
    """Neuer Partner aus einer blanken Nummer — Name ist nachpflegbar."""
    return CleaningPartner(
        partner_id=cleaning_partner_id(account_id, employee.phone_e164),
        account_id=account_id,
        name=employee.phone_e164,
        phone=employee.phone_e164,
        locale=employee.locale,
        property_names=[property_name.strip()],
    )


def _normalize_employees(
    employees: list[PropertyWhatsAppEmployee] | list[str],
) -> list[PropertyWhatsAppEmployee]:
    result: list[PropertyWhatsAppEmployee] = []
    for entry in employees:
        if isinstance(entry, PropertyWhatsAppEmployee):
            result.append(entry)
            continue
        phone = entry.strip()
        if phone:
            result.append(
                PropertyWhatsAppEmployee(
                    phone_e164=phone,
                    locale=DEFAULT_EMPLOYEE_LOCALE,
                )
            )
    return result
