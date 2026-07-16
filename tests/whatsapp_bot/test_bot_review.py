"""Review per Chat, lesender Teil: Übersicht, Liste, Details."""

from __future__ import annotations

from typing import Any

from backend.features.whatsapp_bot.deps import BotDeps
from backend.infrastructure.repositories.user_repository import UserRepository
from tests.whatsapp_bot.conftest import (
    FakeMessenger,
    make_bot,
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


def test_uebersicht_zaehlt_nach_intent(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "new_booking", "Coosemans")
    _seed(review_deps, mock_db, "c2", "new_booking", "Jutta")
    _seed(review_deps, mock_db, "c3", "cancellation", "Louw")

    bot = make_bot(
        review_deps, user_repo, fake_messenger, {"action": "review_uebersicht"}
    )
    bot.handle(meta_text_payload("Review"), _ACC)

    text = fake_messenger.all_texts
    assert "3 offen" in text
    assert "2 Neue Buchungen" in text
    assert "1 Stornos" in text


def test_uebersicht_bei_leerer_warteschlange(
    review_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    seed_owner(user_repo, _ACC, _OWNER)
    bot = make_bot(
        review_deps, user_repo, fake_messenger, {"action": "review_uebersicht"}
    )
    bot.handle(meta_text_payload("Review"), _ACC)
    assert "alles abgearbeitet" in fake_messenger.all_texts


def test_liste_nummeriert_und_filtert(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "new_booking", "Coosemans")
    _seed(review_deps, mock_db, "c2", "cancellation", "Louw")

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_liste", "review_intent": "new_booking"},
    )
    bot.handle(meta_text_payload("Zeig mir alle neuen Buchungen"), _ACC)

    text = fake_messenger.all_texts
    assert "*1.*" in text
    assert "Coosemans" in text
    assert "Louw" not in text  # Storno rausgefiltert


def test_details_zeigt_entwurf(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "new_booking", "Coosemans")

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_details", "position": 1},
    )
    bot.handle(meta_text_payload("Zeig mir Buchung 1"), _ACC)

    text = fake_messenger.all_texts
    assert "Coosemans" in text
    assert "vielen Dank für Ihre Buchung" in text


def test_details_ohne_nummer_fragt_nach(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "new_booking", "Coosemans")

    bot = make_bot(review_deps, user_repo, fake_messenger, {"action": "review_details"})
    bot.handle(meta_text_payload("Zeig mir die Buchung"), _ACC)
    assert "Welchen Eintrag meinst du" in fake_messenger.all_texts


def test_manager_darf_lesen(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    seed_manager(user_repo, _ACC, _MANAGER)
    _seed(review_deps, mock_db, "c1", "new_booking", "Coosemans")

    bot = make_bot(
        review_deps, user_repo, fake_messenger, {"action": "review_uebersicht"}
    )
    bot.handle(meta_text_payload("Review", sender=_MANAGER), _ACC)
    assert "1 offen" in fake_messenger.all_texts


def test_ohne_review_verdrahtung_klare_ansage(
    bot_deps: BotDeps, user_repo: UserRepository, fake_messenger: FakeMessenger
) -> None:
    """review_repo=None darf nicht crashen."""
    seed_owner(user_repo, _ACC, _OWNER)
    bot = make_bot(bot_deps, user_repo, fake_messenger, {"action": "review_uebersicht"})
    bot.handle(meta_text_payload("Review"), _ACC)
    assert "nicht verfügbar" in fake_messenger.all_texts
