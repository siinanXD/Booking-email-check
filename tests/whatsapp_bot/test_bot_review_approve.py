"""Review per Chat, schreibender Teil: Freigabe einzeln und als Sammelaktion.

Freigeben verschickt nie etwas an Gäste, löst aber WhatsApp an Mitarbeiter aus
— deshalb hier besonders geprüft: nie ohne Bestätigung, nie für Manager.
"""

from __future__ import annotations

from typing import Any

from backend.features.cleaning.models import CleaningPartner
from backend.features.whatsapp_bot.deps import BotDeps
from backend.infrastructure.repositories.user_repository import UserRepository
from tests.whatsapp_bot.conftest import (
    FakeMessenger,
    FakeReviewRouter,
    make_bot,
    meta_button_payload,
    meta_text_payload,
    seed_manager,
    seed_owner,
    seed_review,
)

_ACC = "acc-1"
_OWNER = "4915711111111"
_MANAGER = "4915733333333"
_PROP = "Münzbach Ferienzimmer"


def _seed(deps: BotDeps, db: Any, cid: str, intent: str, guest: str) -> None:
    seed_review(
        deps,
        db,
        _ACC,
        correlation_id=cid,
        intent=intent,
        guest=guest,
        property_name=_PROP,
    )


def _click(bot: Any, messenger: FakeMessenger, index: int, msg_id: str) -> None:
    _, _, buttons = messenger.buttons[-1]
    bot.handle(
        meta_button_payload(buttons[index].id, sender=_OWNER, message_id=msg_id), _ACC
    )


def test_freigeben_braucht_bestaetigung_und_nennt_empfaenger(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
    router: FakeReviewRouter,
) -> None:
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "new_booking", "Coosemans")
    review_deps.cleaning_partner_repo.upsert(
        CleaningPartner(
            partner_id="p1",
            name="Dennis",
            phone="+4915799999999",
            property_names=[_PROP],
        ),
        account_id=_ACC,
    )

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_freigeben", "position": 1},
    )
    bot.handle(meta_text_payload("Buchung 1 freigeben"), _ACC)

    assert router.approved == []  # erst die Rückfrage
    text = fake_messenger.all_texts
    assert "Freigeben?" in text
    assert "Dennis" in text  # wer benachrichtigt wird
    assert "An den Gast geht nichts raus" in text

    _click(bot, fake_messenger, 0, "w.ok")
    assert router.approved == ["c1"]
    assert "1 Eintrag freigegeben" in fake_messenger.all_texts


def test_ohne_mitarbeiter_sagt_der_bot_das(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "cancellation", "Louw")

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_freigeben", "position": 1},
    )
    bot.handle(meta_text_payload("Storno 1 freigeben"), _ACC)
    assert "Es wird niemand benachrichtigt" in fake_messenger.all_texts


def test_abbrechen_gibt_nichts_frei(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
    router: FakeReviewRouter,
) -> None:
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "new_booking", "Coosemans")

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_freigeben", "position": 1},
    )
    bot.handle(meta_text_payload("Buchung 1 freigeben"), _ACC)
    _click(bot, fake_messenger, 1, "w.no")
    assert router.approved == []
    assert "Abgebrochen" in fake_messenger.all_texts


def test_nummer_bezieht_sich_auf_letzte_liste(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
    router: FakeReviewRouter,
) -> None:
    """Nach gefilterter Liste meint "1" den ersten Eintrag DIESER Liste."""
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "cancellation", "Louw")
    _seed(review_deps, mock_db, "c2", "new_booking", "Coosemans")

    listing_bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_liste", "review_intent": "new_booking"},
    )
    listing_bot.handle(meta_text_payload("Zeig mir alle neuen Buchungen"), _ACC)

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_freigeben", "position": 1},
    )
    bot.handle(meta_text_payload("Buchung 1 freigeben", message_id="wamid.2"), _ACC)
    _click(bot, fake_messenger, 0, "w.ok")
    assert router.approved == ["c2"]  # die Neubuchung, nicht der Storno


def test_position_ausserhalb_der_liste(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
    router: FakeReviewRouter,
) -> None:
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "new_booking", "Coosemans")

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_freigeben", "position": 5},
    )
    bot.handle(meta_text_payload("Buchung 5 freigeben"), _ACC)
    assert router.approved == []
    assert "keine Nummer" in fake_messenger.all_texts
    assert fake_messenger.buttons == []


def test_sammelfreigabe(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
    router: FakeReviewRouter,
) -> None:
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "new_booking", "Coosemans")
    _seed(review_deps, mock_db, "c2", "new_booking", "Jutta")
    _seed(review_deps, mock_db, "c3", "cancellation", "Louw")

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_alle_freigeben", "review_intent": "new_booking"},
    )
    bot.handle(meta_text_payload("Alle neuen Buchungen freigeben"), _ACC)
    assert "Alle 2 freigeben?" in fake_messenger.all_texts

    _click(bot, fake_messenger, 0, "w.ok")
    assert sorted(router.approved) == ["c1", "c2"]
    assert "c3" not in router.approved  # der Storno bleibt liegen


def test_teilfehler_wird_gemeldet(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
    router: FakeReviewRouter,
) -> None:
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "new_booking", "Coosemans")
    _seed(review_deps, mock_db, "c2", "new_booking", "Jutta")
    router.fail_on = {"c2"}

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_alle_freigeben", "review_intent": "new_booking"},
    )
    bot.handle(meta_text_payload("Alle neuen Buchungen freigeben"), _ACC)
    _click(bot, fake_messenger, 0, "w.ok")
    assert "1 freigegeben, 1 fehlgeschlagen" in fake_messenger.all_texts


def test_manager_darf_nicht_freigeben(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
    router: FakeReviewRouter,
) -> None:
    seed_manager(user_repo, _ACC, _MANAGER)
    _seed(review_deps, mock_db, "c1", "new_booking", "Coosemans")

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_freigeben", "position": 1},
    )
    bot.handle(meta_text_payload("Buchung 1 freigeben", sender=_MANAGER), _ACC)
    assert router.approved == []
    assert "fehlt dir leider die Berechtigung" in fake_messenger.all_texts
