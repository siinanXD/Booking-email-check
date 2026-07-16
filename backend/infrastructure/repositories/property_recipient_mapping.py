"""Empfänger-Modelle und ihre Abbildung auf `CleaningPartner`.

Ein Mitarbeiter existiert nur einmal — als ``CleaningPartner`` (partner-zentrisch,
eine Person → ihre Objekte). Diese Datei übersetzt ihn in die objekt-zentrische
Sicht (ein Objekt → seine Empfänger) und zurück. Kein Datenbankzugriff.

Liegt getrennt vom Repository, weil beides zusammen über dem 300-Zeilen-Limit
läge — und weil die Feld-Übersetzung die Stelle ist, an der man nachliest, was
beim Speichern mit Name und Testmodus passiert.
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

_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")


class PropertyWhatsAppEmployee(BaseModel):
    """Mitarbeiter-Empfänger mit Name, Sprache und Testmodus.

    ``name`` und ``test_mode`` sind ``None``-bar und bedeuten dann *nicht
    anfassen*: die Einstellungsseite schickt Mitarbeiter ohne diese Felder, und
    ein leerer Wert dürfte den am Objektprofil gepflegten Namen nicht löschen.
    """

    phone_e164: str
    locale: str = DEFAULT_EMPLOYEE_LOCALE
    name: str | None = None
    test_mode: bool | None = None

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
    """Mitarbeiter einer Unterkunft."""

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


def to_employees(
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
                name=partner.name,
                test_mode=partner.test_mode,
            )
        )
    return result


def apply_employee(
    partner: CleaningPartner, employee: PropertyWhatsAppEmployee
) -> None:
    """Übernimmt die Felder des Empfängers auf den Partner.

    ``None`` heißt *nicht anfassen* — sonst würde die Einstellungsseite, die
    Mitarbeiter ohne Name/Testmodus schickt, beides stillschweigend löschen.
    Adresse und Ansprechpartner kennt die Empfänger-Sicht gar nicht; sie bleiben
    deshalb immer erhalten.
    """
    partner.locale = employee.locale
    if employee.name is not None and employee.name.strip():
        partner.name = employee.name.strip()
    if employee.test_mode is not None:
        partner.test_mode = employee.test_mode


def attach(partner: CleaningPartner, name: str) -> None:
    """Ordnet dem Partner ein Objekt zu (idempotent, case-insensitiv)."""
    if name.strip().lower() not in {n.strip().lower() for n in partner.property_names}:
        partner.property_names = [*partner.property_names, name.strip()]


def detach(partner: CleaningPartner, name: str) -> None:
    """Löst die Zuordnung des Partners zu einem Objekt."""
    key = name.strip().lower()
    partner.property_names = [
        n for n in partner.property_names if n.strip().lower() != key
    ]


def new_partner(
    account_id: str,
    property_name: str,
    employee: PropertyWhatsAppEmployee,
) -> CleaningPartner:
    """Neuer Partner. Ohne Namen dient die Nummer als Platzhalter."""
    return CleaningPartner(
        partner_id=cleaning_partner_id(account_id, employee.phone_e164),
        account_id=account_id,
        name=(employee.name or "").strip() or employee.phone_e164,
        phone=employee.phone_e164,
        locale=employee.locale,
        test_mode=bool(employee.test_mode),
        property_names=[property_name.strip()],
    )


def normalize_employees(
    employees: list[PropertyWhatsAppEmployee] | list[str],
) -> list[PropertyWhatsAppEmployee]:
    """Akzeptiert auch blanke Telefonnummern (Altbestand der Einstellungs-API)."""
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
