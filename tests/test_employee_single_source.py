"""Mitarbeiter haben genau eine Quelle: `cleaning_partners`.

Regression: Der WhatsApp-Bot schrieb Mitarbeiter nach `cleaning_partners`, die
Weboberfläche las `property_whatsapp_recipients`. Per Chat angelegte Mitarbeiter
tauchten im Web nie auf, und ein Partner unter einem abweichenden Objektnamen
bekam nie einen Putzauftrag.
"""

from __future__ import annotations

from backend.features.cleaning.models import CleaningPartner
from backend.infrastructure.repositories.cleaning_partner_repository import (
    CleaningPartnerRepository,
)
from backend.infrastructure.repositories.property_recipient_repository import (
    PropertyRecipientRepository,
    PropertyWhatsAppEmployee,
)

ACCOUNT = "acc-1"


def _partner(
    partner_id: str, phone: str, props: list[str], **kw: object
) -> CleaningPartner:
    return CleaningPartner(
        partner_id=partner_id,
        account_id=ACCOUNT,
        name=kw.pop("name", "Putzkraft"),  # type: ignore[arg-type]
        phone=phone,
        property_names=props,
        **kw,  # type: ignore[arg-type]
    )


def test_bot_angelegter_partner_ist_im_web_sichtbar(mock_db):
    """Der ursprünglich gemeldete Fehler: Chat legt an, Web zeigt nichts."""
    CleaningPartnerRepository(mock_db).upsert(
        _partner("p1", "+491701234567", ["Villa Sonne"], name="Dennis"),
        account_id=ACCOUNT,
    )

    employees = PropertyRecipientRepository(mock_db).get_employees(
        "Villa Sonne", account_id=ACCOUNT
    )

    assert [e.phone_e164 for e in employees] == ["+491701234567"]


def test_web_schreibt_in_dieselbe_quelle_wie_der_bot(mock_db):
    """Was das Web speichert, muss der Putzplan als Partner wiederfinden."""
    recipients = PropertyRecipientRepository(mock_db)
    recipients.upsert(
        ACCOUNT,
        "Villa Sonne",
        [PropertyWhatsAppEmployee(phone_e164="+491701234567", locale="de")],
    )

    partners = CleaningPartnerRepository(mock_db).find_for_property(
        "Villa Sonne", account_id=ACCOUNT
    )

    assert [p.phone for p in partners] == ["+491701234567"]


def test_testmodus_partner_bekommt_keine_echte_nachricht(mock_db):
    """Testmodus darf nicht über die Empfänger-Sicht zum Versand durchrutschen."""
    CleaningPartnerRepository(mock_db).upsert(
        _partner("p1", "+491701234567", ["Villa Sonne"], test_mode=True),
        account_id=ACCOUNT,
    )
    recipients = PropertyRecipientRepository(mock_db)

    assert recipients.get_phones("Villa Sonne", account_id=ACCOUNT) == []
    # In der Oberfläche soll er trotzdem sichtbar sein.
    assert recipients.get_phones(
        "Villa Sonne", account_id=ACCOUNT, include_test_mode=True
    ) == ["+491701234567"]


def test_inaktiver_partner_ist_kein_empfaenger(mock_db):
    CleaningPartnerRepository(mock_db).upsert(
        _partner("p1", "+491701234567", ["Villa Sonne"], active=False),
        account_id=ACCOUNT,
    )

    assert (
        PropertyRecipientRepository(mock_db).get_phones(
            "Villa Sonne", account_id=ACCOUNT
        )
        == []
    )


def test_umbenennung_zieht_die_zuordnung_mit(mock_db):
    """Regression: namensbasierte Zuordnung verwaiste beim Umbenennen still."""
    partners = CleaningPartnerRepository(mock_db)
    partners.upsert(
        _partner("p1", "+491701234567", ["Villa Sonne"]), account_id=ACCOUNT
    )
    recipients = PropertyRecipientRepository(mock_db)

    recipients.rename_property(ACCOUNT, "Villa Sonne", "Villa Sonnenschein")

    assert recipients.get_phones("Villa Sonnenschein", account_id=ACCOUNT) == [
        "+491701234567"
    ]
    assert recipients.get_phones("Villa Sonne", account_id=ACCOUNT) == []


def test_upsert_loest_entfernte_mitarbeiter_ab(mock_db):
    recipients = PropertyRecipientRepository(mock_db)
    recipients.upsert(
        ACCOUNT,
        "Villa Sonne",
        [
            PropertyWhatsAppEmployee(phone_e164="+491701234567"),
            PropertyWhatsAppEmployee(phone_e164="+491709999999"),
        ],
    )

    recipients.upsert(
        ACCOUNT, "Villa Sonne", [PropertyWhatsAppEmployee(phone_e164="+491701234567")]
    )

    assert recipients.get_phones("Villa Sonne", account_id=ACCOUNT) == ["+491701234567"]


def test_upsert_erhaelt_name_und_testmodus_des_partners(mock_db):
    """Reconcile statt Überschreiben: Stammdaten dürfen nicht verlorengehen."""
    partners = CleaningPartnerRepository(mock_db)
    partners.upsert(
        _partner("p1", "+491701234567", ["Villa Sonne"], name="Dennis", test_mode=True),
        account_id=ACCOUNT,
    )

    PropertyRecipientRepository(mock_db).upsert(
        ACCOUNT,
        "Villa Sonne",
        [PropertyWhatsAppEmployee(phone_e164="+491701234567", locale="en")],
    )

    partner = partners.get("p1", account_id=ACCOUNT)
    assert partner is not None
    assert partner.name == "Dennis"
    assert partner.test_mode is True
    assert partner.locale == "en"


def test_ein_partner_mehrere_objekte_erscheint_bei_beiden(mock_db):
    CleaningPartnerRepository(mock_db).upsert(
        _partner("p1", "+491701234567", ["Villa Sonne", "Haus Meer"]),
        account_id=ACCOUNT,
    )
    recipients = PropertyRecipientRepository(mock_db)

    assert recipients.get_phones("Villa Sonne", account_id=ACCOUNT) == ["+491701234567"]
    assert recipients.get_phones("Haus Meer", account_id=ACCOUNT) == ["+491701234567"]
    assert {r.property_name for r in recipients.list_all(ACCOUNT)} == {
        "Villa Sonne",
        "Haus Meer",
    }


def test_fremder_mandant_sieht_nichts(mock_db):
    CleaningPartnerRepository(mock_db).upsert(
        _partner("p1", "+491701234567", ["Villa Sonne"]), account_id=ACCOUNT
    )

    assert (
        PropertyRecipientRepository(mock_db).get_phones(
            "Villa Sonne", account_id="acc-2"
        )
        == []
    )


def test_name_und_testmodus_sind_vom_objekt_aus_pflegbar(mock_db):
    """Das Objektprofil ist seit dem Wegfall des Putzpartner-Bereichs der
    einzige Editor — ohne diese Felder hiesse jeder neue Mitarbeiter fuer immer
    wie seine Telefonnummer."""
    recipients = PropertyRecipientRepository(mock_db)

    recipients.upsert(
        ACCOUNT,
        "Villa Sonne",
        [
            PropertyWhatsAppEmployee(
                phone_e164="+491701234567", name="Dennis", test_mode=True
            )
        ],
    )

    partner = CleaningPartnerRepository(mock_db).find_for_property(
        "Villa Sonne", account_id=ACCOUNT
    )[0]
    assert partner.name == "Dennis"
    assert partner.test_mode is True


def test_neuer_mitarbeiter_ohne_namen_bekommt_die_nummer(mock_db):
    recipients = PropertyRecipientRepository(mock_db)

    recipients.upsert(
        ACCOUNT, "Villa Sonne", [PropertyWhatsAppEmployee(phone_e164="+491701234567")]
    )

    partner = CleaningPartnerRepository(mock_db).find_for_property(
        "Villa Sonne", account_id=ACCOUNT
    )[0]
    assert partner.name == "+491701234567"


def test_aufrufer_ohne_name_loeschen_den_namen_nicht(mock_db):
    """Die Einstellungsseite schickt Mitarbeiter ohne Name/Testmodus. `None`
    muss "nicht anfassen" heissen, sonst radiert sie die Pflege vom Objekt aus."""
    partners = CleaningPartnerRepository(mock_db)
    partners.upsert(
        _partner("p1", "+491701234567", ["Villa Sonne"], name="Dennis", test_mode=True),
        account_id=ACCOUNT,
    )

    PropertyRecipientRepository(mock_db).upsert(
        ACCOUNT, "Villa Sonne", ["+491701234567"]
    )

    partner = partners.get("p1", account_id=ACCOUNT)
    assert partner is not None
    assert partner.name == "Dennis"
    assert partner.test_mode is True


def test_mehrere_mitarbeiter_an_einem_objekt(mock_db):
    """Der Putzpartner-Bereich konnte das; das Objektprofil muss es auch."""
    recipients = PropertyRecipientRepository(mock_db)

    recipients.upsert(
        ACCOUNT,
        "Villa Sonne",
        [
            PropertyWhatsAppEmployee(phone_e164="+491701234567", name="Dennis"),
            PropertyWhatsAppEmployee(phone_e164="+491709999999", name="Anne"),
        ],
    )

    employees = recipients.get_employees("Villa Sonne", account_id=ACCOUNT)
    assert sorted(e.name or "" for e in employees) == ["Anne", "Dennis"]


def test_name_wirkt_objektuebergreifend(mock_db):
    """Gleiche Nummer = dieselbe Person. Am zweiten Objekt umbenannt heisst sie
    auch am ersten so — sonst gaebe es sie wieder doppelt."""
    recipients = PropertyRecipientRepository(mock_db)
    recipients.upsert(
        ACCOUNT,
        "Villa Sonne",
        [PropertyWhatsAppEmployee(phone_e164="+491701234567", name="D. Wasinski")],
    )

    recipients.upsert(
        ACCOUNT,
        "Haus Meer",
        [PropertyWhatsAppEmployee(phone_e164="+491701234567", name="Dennis Wasinski")],
    )

    employees = recipients.get_employees("Villa Sonne", account_id=ACCOUNT)
    assert [e.name for e in employees] == ["Dennis Wasinski"]
