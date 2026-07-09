"""End-to-End-Tests des Bot-Service (Fakes für LLM und Messenger)."""

from __future__ import annotations

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
_CLEANER_PHONE = "4915722222222"


def _seed_owner(user_repo: UserRepository) -> None:
    user = user_repo.create(
        "owner@test.local",
        "hash",
        account_id=_ACC,
        role="owner",
        first_name="Olaf",
    )
    user_repo.update_whatsapp_profile(
        user.id, whatsapp_phone_e164=f"+{_OWNER_PHONE}", whatsapp_enabled=True
    )


def _seed_cleaner(deps: BotDeps) -> None:
    deps.cleaning_partner_repo.upsert(
        CleaningPartner(partner_id="p1", name="Petra", phone=f"+{_CLEANER_PHONE}"),
        account_id=_ACC,
    )


def test_unbekannte_nummer_wird_hoeflich_abgelehnt(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    bot = make_bot(bot_deps, user_repo, fake_messenger)
    status = bot.handle(meta_text_payload("Hallo", sender="49111"), _ACC)
    assert status == "unknown_sender"
    assert "keinem Konto zugeordnet" in fake_messenger.all_texts


def test_hilfe_zeigt_willkommen(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_owner(user_repo)
    bot = make_bot(bot_deps, user_repo, fake_messenger, {"action": "hilfe"})
    status = bot.handle(meta_text_payload("Hi", sender=_OWNER_PHONE), _ACC)
    assert status == "handled"
    assert "Putzpläne erstellen" in fake_messenger.all_texts


def test_duplikat_wird_verworfen(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_owner(user_repo)
    bot = make_bot(bot_deps, user_repo, fake_messenger, {"action": "hilfe"})
    payload = meta_text_payload("Hi", sender=_OWNER_PHONE, message_id="wamid.x")
    assert bot.handle(payload, _ACC) == "handled"
    assert bot.handle(payload, _ACC) == "duplicate"
    assert len(fake_messenger.texts) == 1


def test_cleaner_darf_keine_buchungen_sehen(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_cleaner(bot_deps)
    bot = make_bot(
        bot_deps, user_repo, fake_messenger, {"action": "buchungen_anzeigen"}
    )
    bot.handle(meta_text_payload("Buchungen?", sender=_CLEANER_PHONE), _ACC)
    assert "fehlt dir leider die Berechtigung" in fake_messenger.all_texts


def test_cleaner_putzplan_wird_zu_eigenen_terminen(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_cleaner(bot_deps)
    bot = make_bot(
        bot_deps, user_repo, fake_messenger, {"action": "putzplan_erstellen"}
    )
    status = bot.handle(meta_text_payload("Putzplan", sender=_CLEANER_PHONE), _ACC)
    assert status == "handled"
    assert "Deine Termine" in fake_messenger.all_texts


def test_mitarbeiter_anlegen_mit_bestaetigung(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    """Kompletter Flow: Anfrage → Buttons → Confirm → DB-Write + Audit."""
    _seed_owner(user_repo)
    bot = make_bot(
        bot_deps,
        user_repo,
        fake_messenger,
        {
            "action": "mitarbeiter_anlegen",
            "person_name": "Maria Neu",
            "person_phone": "+49 157 3333 3333",
        },
    )
    bot.handle(meta_text_payload("Leg Maria an", sender=_OWNER_PHONE), _ACC)

    # Noch KEIN Schreibzugriff — nur Bestätigungs-Buttons
    assert bot_deps.cleaning_partner_repo.list_partners(account_id=_ACC) == []
    assert len(fake_messenger.buttons) == 1
    _, text, buttons = fake_messenger.buttons[0]
    assert "Maria Neu" in text
    confirm = next(b for b in buttons if b.id.startswith("confirm_"))

    bot.handle(
        meta_button_payload(confirm.id, sender=_OWNER_PHONE, message_id="wamid.2"),
        _ACC,
    )
    partners = bot_deps.cleaning_partner_repo.list_partners(account_id=_ACC)
    assert len(partners) == 1
    assert partners[0].name == "Maria Neu"
    assert partners[0].phone == "+4915733333333"

    audit = bot_deps.audit_repo.list_recent(account_id=_ACC)
    confirmed = [e for e in audit if e.confirmed]
    assert len(confirmed) == 1
    assert confirmed[0].action == "mitarbeiter_anlegen"


def test_abbrechen_schreibt_nichts(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_owner(user_repo)
    bot = make_bot(
        bot_deps,
        user_repo,
        fake_messenger,
        {
            "action": "objekt_anlegen",
            "property_name": "FeWo Neu",
        },
    )
    bot.handle(meta_text_payload("Neues Objekt FeWo Neu", sender=_OWNER_PHONE), _ACC)
    _, _, buttons = fake_messenger.buttons[0]
    cancel = next(b for b in buttons if b.id.startswith("cancel_"))
    bot.handle(
        meta_button_payload(cancel.id, sender=_OWNER_PHONE, message_id="wamid.2"),
        _ACC,
    )
    assert bot_deps.property_repo.list_all(account_id=_ACC) == []
    assert "Abgebrochen" in fake_messenger.all_texts


def test_veralteter_button_wird_abgelehnt(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_owner(user_repo)
    bot = make_bot(bot_deps, user_repo, fake_messenger)
    bot.handle(
        meta_button_payload("confirm_gibtesnicht", sender=_OWNER_PHONE),
        _ACC,
    )
    assert "nicht mehr gültig" in fake_messenger.all_texts


def test_objekt_zuweisen_flow(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_owner(user_repo)
    _seed_cleaner(bot_deps)
    bot = make_bot(
        bot_deps,
        user_repo,
        fake_messenger,
        {
            "action": "objekt_zuweisen",
            "person_name": "Petra",
            "property_name": "FeWo Seeblick",
        },
    )
    bot.handle(meta_text_payload("Petra macht Seeblick", sender=_OWNER_PHONE), _ACC)
    _, _, buttons = fake_messenger.buttons[0]
    confirm = next(b for b in buttons if b.id.startswith("confirm_"))
    bot.handle(
        meta_button_payload(confirm.id, sender=_OWNER_PHONE, message_id="wamid.2"),
        _ACC,
    )
    partner = bot_deps.cleaning_partner_repo.get("p1", account_id=_ACC)
    assert partner is not None
    assert "FeWo Seeblick" in partner.property_names


def test_audio_ohne_transcriber_bittet_um_text(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_owner(user_repo)
    bot = make_bot(bot_deps, user_repo, fake_messenger)
    payload = meta_text_payload("x", sender=_OWNER_PHONE)
    msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    msg["type"] = "audio"
    msg["audio"] = {"id": "media-1", "mime_type": "audio/ogg"}
    del msg["text"]
    status = bot.handle(payload, _ACC)
    assert status == "handled"
    assert "Sprachnachricht" in fake_messenger.all_texts


def test_unklar_liefert_rueckfrage(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    _seed_owner(user_repo)
    bot = make_bot(bot_deps, user_repo, fake_messenger, {"action": "unklar"})
    bot.handle(meta_text_payload("blubb", sender=_OWNER_PHONE), _ACC)
    assert "nicht verstanden" in fake_messenger.all_texts
