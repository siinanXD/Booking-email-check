"""End-to-End-Tests der Änderungs-Handler (ändern, umbenennen, löschen)."""

from __future__ import annotations

from typing import Any

from backend.core.models.entities import Property
from backend.features.cleaning.models import CleaningPartner
from backend.features.whatsapp_bot.deps import BotDeps
from backend.infrastructure.repositories.user_repository import UserRepository
from tests.whatsapp_bot.conftest import (
    FakeMessenger,
    make_bot,
    meta_button_payload,
    meta_text_payload,
)

_ACC = "acc-1"
_OWNER_PHONE = "4915711111111"
_MANAGER_PHONE = "4915733333333"


def _seed_owner(user_repo: UserRepository) -> None:
    user = user_repo.create(
        "owner@test.local", "hash", account_id=_ACC, role="owner", first_name="Olaf"
    )
    user_repo.update_whatsapp_profile(
        user.id, whatsapp_phone_e164=f"+{_OWNER_PHONE}", whatsapp_enabled=True
    )


def _seed_manager(user_repo: UserRepository) -> None:
    user = user_repo.create(
        "member@test.local", "hash", account_id=_ACC, role="member", first_name="Mara"
    )
    user_repo.update_whatsapp_profile(
        user.id, whatsapp_phone_e164=f"+{_MANAGER_PHONE}", whatsapp_enabled=True
    )


def _seed_partner(deps: BotDeps, *, properties: list[str] | None = None) -> None:
    deps.cleaning_partner_repo.upsert(
        CleaningPartner(
            partner_id="p1",
            name="Anna",
            phone="+4915799999999",
            property_names=properties or [],
        ),
        account_id=_ACC,
    )


def _seed_property(deps: BotDeps, name: str = "Villa Sonne") -> None:
    deps.property_repo.upsert(
        Property(property_id="prop-1", name=name, account_id=_ACC), account_id=_ACC
    )


def _confirm(bot: Any, messenger: FakeMessenger, *, sender: str = _OWNER_PHONE) -> None:
    """Klickt den Bestätigungs-Button der zuletzt gesendeten Rückfrage."""
    _, _, buttons = messenger.buttons[-1]
    bot.handle(
        meta_button_payload(buttons[0].id, sender=sender, message_id="wamid.ok"), _ACC
    )


def test_mitarbeiter_nummer_aendern(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_owner(user_repo)
    _seed_partner(bot_deps)
    bot = make_bot(
        bot_deps,
        user_repo,
        fake_messenger,
        {
            "action": "mitarbeiter_aendern",
            "person_name": "Anna",
            "person_phone": "+4917012345678",
        },
    )
    bot.handle(meta_text_payload("Annas Nummer ist +4917012345678"), _ACC)
    assert "Mitarbeiter ändern?" in fake_messenger.all_texts

    _confirm(bot, fake_messenger)
    partner = bot_deps.cleaning_partner_repo.get("p1", account_id=_ACC)
    assert partner is not None
    assert partner.phone == "+4917012345678"
    assert partner.name == "Anna"


def test_mitarbeiter_umbenennen(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_owner(user_repo)
    _seed_partner(bot_deps)
    bot = make_bot(
        bot_deps,
        user_repo,
        fake_messenger,
        {
            "action": "mitarbeiter_aendern",
            "person_name": "Anna",
            "neuer_name": "Anna Müller",
        },
    )
    bot.handle(meta_text_payload("Anna heißt jetzt Anna Müller"), _ACC)
    _confirm(bot, fake_messenger)
    partner = bot_deps.cleaning_partner_repo.get("p1", account_id=_ACC)
    assert partner is not None
    assert partner.name == "Anna Müller"


def test_aendern_ohne_zielwert_fragt_nach(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_owner(user_repo)
    _seed_partner(bot_deps)
    bot = make_bot(
        bot_deps,
        user_repo,
        fake_messenger,
        {"action": "mitarbeiter_aendern", "person_name": "Anna"},
    )
    bot.handle(meta_text_payload("Ändere Anna"), _ACC)
    assert "Name oder Telefonnummer" in fake_messenger.all_texts
    assert fake_messenger.buttons == []


def test_objekt_umbenennen_zieht_zuordnung_mit(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_owner(user_repo)
    _seed_property(bot_deps)
    _seed_partner(bot_deps, properties=["Villa Sonne"])
    bot = make_bot(
        bot_deps,
        user_repo,
        fake_messenger,
        {
            "action": "objekt_bearbeiten",
            "property_name": "Villa Sonne",
            "neuer_name": "Villa Mond",
        },
    )
    bot.handle(meta_text_payload("Villa Sonne heißt jetzt Villa Mond"), _ACC)
    _confirm(bot, fake_messenger)

    prop = bot_deps.property_repo.get_by_id("prop-1", account_id=_ACC)
    assert prop is not None
    assert prop.name == "Villa Mond"
    partner = bot_deps.cleaning_partner_repo.get("p1", account_id=_ACC)
    assert partner is not None
    assert partner.property_names == ["Villa Mond"]


def test_objekt_loeschen_archiviert_und_loest_zuordnung(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_owner(user_repo)
    _seed_property(bot_deps)
    _seed_partner(bot_deps, properties=["Villa Sonne"])
    bot = make_bot(
        bot_deps,
        user_repo,
        fake_messenger,
        {"action": "objekt_loeschen", "property_name": "Villa Sonne"},
    )
    bot.handle(meta_text_payload("Lösch Villa Sonne"), _ACC)
    _confirm(bot, fake_messenger)

    assert bot_deps.property_repo.list_all(account_id=_ACC) == []
    # Soft-Delete: der Datensatz bleibt für historische Aufträge auflösbar.
    archived = bot_deps.property_repo.list_all(account_id=_ACC, include_inactive=True)
    assert [p.name for p in archived] == ["Villa Sonne"]
    partner = bot_deps.cleaning_partner_repo.get("p1", account_id=_ACC)
    assert partner is not None
    assert partner.property_names == []


def test_zuordnung_entziehen(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_owner(user_repo)
    _seed_partner(bot_deps, properties=["Villa Sonne", "Haus Nord"])
    bot = make_bot(
        bot_deps,
        user_repo,
        fake_messenger,
        {
            "action": "objekt_entziehen",
            "person_name": "Anna",
            "property_name": "Villa Sonne",
        },
    )
    bot.handle(meta_text_payload("Nimm Anna die Villa Sonne weg"), _ACC)
    _confirm(bot, fake_messenger)

    partner = bot_deps.cleaning_partner_repo.get("p1", account_id=_ACC)
    assert partner is not None
    assert partner.property_names == ["Haus Nord"]


def test_entziehen_ohne_bestehende_zuordnung(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_owner(user_repo)
    _seed_partner(bot_deps, properties=["Haus Nord"])
    bot = make_bot(
        bot_deps,
        user_repo,
        fake_messenger,
        {
            "action": "objekt_entziehen",
            "person_name": "Anna",
            "property_name": "Villa Sonne",
        },
    )
    bot.handle(meta_text_payload("Nimm Anna die Villa Sonne weg"), _ACC)
    assert "gar nicht zugeordnet" in fake_messenger.all_texts
    assert fake_messenger.buttons == []


def test_manager_darf_nicht_aendern(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_manager(user_repo)
    _seed_partner(bot_deps)
    bot = make_bot(
        bot_deps,
        user_repo,
        fake_messenger,
        {
            "action": "mitarbeiter_aendern",
            "person_name": "Anna",
            "neuer_name": "Anna Müller",
        },
    )
    bot.handle(
        meta_text_payload("Anna heißt jetzt Anna Müller", sender=_MANAGER_PHONE), _ACC
    )
    assert "fehlt dir leider die Berechtigung" in fake_messenger.all_texts
    partner = bot_deps.cleaning_partner_repo.get("p1", account_id=_ACC)
    assert partner is not None
    assert partner.name == "Anna"


def test_abbrechen_aendert_nichts(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_owner(user_repo)
    _seed_property(bot_deps)
    bot = make_bot(
        bot_deps,
        user_repo,
        fake_messenger,
        {"action": "objekt_loeschen", "property_name": "Villa Sonne"},
    )
    bot.handle(meta_text_payload("Lösch Villa Sonne"), _ACC)
    _, _, buttons = fake_messenger.buttons[-1]
    bot.handle(
        meta_button_payload(buttons[1].id, sender=_OWNER_PHONE, message_id="wamid.no"),
        _ACC,
    )
    assert "Abgebrochen" in fake_messenger.all_texts
    assert len(bot_deps.property_repo.list_all(account_id=_ACC)) == 1
