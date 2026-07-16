"""WhatsApp-Empfänger pro Unterkunft — abgeleitete Sicht auf `cleaning_partners`.

Mitarbeiter lagen früher doppelt vor: der Bot schrieb nach `cleaning_partners`,
die Weboberfläche las `property_whatsapp_recipients`. Die Töpfe liefen auseinander
— per Chat angelegte Mitarbeiter tauchten im Web nie auf. `cleaning_partners` ist
darum die einzige Quelle; hier liegt nur die objekt-zentrische Sicht darauf
(Objekt → Empfänger), während `CleaningPartner` partner-zentrisch bleibt
(Partner → Objekte). Die Schnittstelle bleibt, damit Aufrufer nichts merken.

Modelle und Feld-Übersetzung stehen in ``property_recipient_mapping`` und werden
hier re-exportiert — die bestehenden Importpfade bleiben damit gültig.
"""

from __future__ import annotations

from backend.features.cleaning.identity import cleaning_partner_id
from backend.features.cleaning.models import CleaningPartner
from backend.infrastructure.repositories.cleaning_partner_repository import (
    CleaningPartnerRepository,
)
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.property_recipient_mapping import (
    PropertyWhatsAppEmployee,
    PropertyWhatsAppRecipients,
    apply_employee,
    attach,
    detach,
    new_partner,
    normalize_employees,
    to_employees,
)

__all__ = [
    "PropertyRecipientRepository",
    "PropertyWhatsAppEmployee",
    "PropertyWhatsAppRecipients",
]


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
        """Lädt Mitarbeiter einer Unterkunft.

        Testmodus-Partner bleiben standardmäßig draußen: Aufrufer dieser Methode
        versenden echte Nachrichten. Die Weboberfläche setzt ``include_test_mode``,
        weil sie den Mitarbeiter anzeigen, aber nichts senden will.
        """
        if not property_name or not property_name.strip() or not account_id:
            return []
        partners = self._partners.find_for_property(
            property_name, account_id=account_id
        )
        return to_employees(partners, include_test_mode=include_test_mode)

    def list_all(
        self,
        account_id: str,
        *,
        include_test_mode: bool = False,
    ) -> list[PropertyWhatsAppRecipients]:
        """Alle Unterkunft → Mitarbeiter-Zuordnungen eines Accounts."""
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
                employees=to_employees(partners, include_test_mode=include_test_mode),
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
        """Setzt die Mitarbeiter einer Unterkunft (legt an bzw. löst ab).

        Reconcile statt Überschreiben: Adresse und Ansprechpartner bleiben
        unangetastet, Name und Testmodus auch — sofern der Aufrufer sie ``None``
        lässt (siehe ``apply_employee``).
        """
        name = property_name.strip()
        normalized = normalize_employees(employees)
        if not name:
            return PropertyWhatsAppRecipients(property_name=name, employees=normalized)

        wanted = {e.phone_e164: e for e in normalized}
        for partner in self._partners.find_for_property(name, account_id=account_id):
            phone = (partner.phone or "").strip()
            if phone in wanted:
                apply_employee(partner, wanted.pop(phone))
                attach(partner, name)
                self._partners.upsert(partner, account_id=account_id)
            else:
                detach(partner, name)
                self._partners.upsert(partner, account_id=account_id)

        for employee in wanted.values():
            self._partners.upsert(
                self._attach_or_create(account_id, name, employee),
                account_id=account_id,
            )
        return PropertyWhatsAppRecipients(property_name=name, employees=normalized)

    def _attach_or_create(
        self,
        account_id: str,
        property_name: str,
        employee: PropertyWhatsAppEmployee,
    ) -> CleaningPartner:
        """Bestehende Person um ein Objekt erweitern, sonst neu anlegen.

        Die partner_id leitet sich aus der Telefonnummer ab. Ohne diese Prüfung
        würde ``new_partner`` denselben Datensatz überschreiben: dieselbe Person
        einem zweiten Objekt zuzuordnen hätte ihr das erste weggenommen.
        Deaktivierte werden dabei reaktiviert — wer sie erneut zuordnet, will
        sie offensichtlich wieder im Einsatz.
        """
        existing = self._partners.get(
            cleaning_partner_id(account_id, employee.phone_e164),
            account_id=account_id,
        )
        if existing is None:
            return new_partner(account_id, property_name, employee)
        apply_employee(existing, employee)
        attach(existing, property_name)
        existing.active = True
        return existing

    def replace_all(
        self,
        account_id: str,
        items: list[tuple[str, list[PropertyWhatsAppEmployee]]],
    ) -> None:
        """Ersetzt die gesamte Mitarbeiter-Liste eines Accounts."""
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
            detach(partner, old)
            attach(partner, new)
            self._partners.upsert(partner, account_id=account_id)
