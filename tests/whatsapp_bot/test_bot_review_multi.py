"""Mehrfach-Freigabe: "Buchung 1 und 3 freigeben".

Vorher ging nur einzeln oder alles. Wer drei von zehn Einträgen freigeben
wollte, musste dreimal denselben Dialog durchklicken.

Die Auflösung passiert beim Befehl, nicht beim Klick: die PendingAction trägt
die correlation_ids, damit eine zwischenzeitlich eingetroffene Mail die Auswahl
nicht verschiebt.
"""

from __future__ import annotations

from typing import Any

from backend.features.whatsapp_bot.deps import BotDeps
from backend.features.whatsapp_bot.intent_service import _positions
from backend.infrastructure.repositories.user_repository import UserRepository
from tests.whatsapp_bot.conftest import (
    FakeMessenger,
    make_bot,
    meta_button_payload,
    meta_text_payload,
    seed_owner,
    seed_review,
)

_ACC = "acc-1"
_OWNER = "4915711111111"
_PROP = "Münzbach Ferienzimmer"


def _seed(deps: BotDeps, db: Any, cid: str, guest: str) -> None:
    seed_review(
        deps,
        db,
        _ACC,
        correlation_id=cid,
        intent="new_booking",
        guest=guest,
        property_name=_PROP,
    )


_GUESTS = {"c1": "Coosemans", "c2": "Jutta", "c3": "Schaub"}


def _seed_three(deps: BotDeps, db: Any) -> None:
    for cid, guest in _GUESTS.items():
        _seed(deps, db, cid, guest)


def _list_first(
    deps: BotDeps,
    user_repo: UserRepository,
    messenger: FakeMessenger,
) -> list[str]:
    """Erst auflisten, dann auswählen — so nummeriert der Bot auch echt.

    Gibt die correlation_ids in der gezeigten Reihenfolge zurück. Die Sortierung
    der Warteschlange ist nichts, was ein Test vorwegnehmen sollte: sie ist nicht
    die Seed-Reihenfolge, und genau daran sind meine ersten Erwartungen zerbrochen.
    """
    bot = make_bot(deps, user_repo, messenger, {"action": "review_liste"})
    bot.handle(meta_text_payload("Zeig mir die Liste", message_id="wamid.list"), _ACC)
    listing = messenger.texts[-1][1]
    return sorted(_GUESTS, key=lambda cid: listing.index(_GUESTS[cid]))


# --- Parser ---------------------------------------------------------------


def test_parser_liest_mehrere_nummern() -> None:
    assert _positions([1, 3], None) == [1, 3]


def test_parser_akzeptiert_strings_und_dedupliziert() -> None:
    """Das LLM liefert Nummern mal als Zahl, mal als String."""
    assert _positions(["1", 3, "3", 2], None) == [1, 3, 2]


def test_parser_faellt_auf_das_alte_feld_zurueck() -> None:
    """Bleibt das Modell beim alten `position`, darf das nicht ins Leere laufen."""
    assert _positions(None, 2) == [2]


def test_parser_ignoriert_bool_und_null() -> None:
    assert _positions([True, 0, -1, None], None) == []


# --- Verhalten ------------------------------------------------------------


def test_auswahl_fragt_mit_namen_nach(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    """Wer per Nummer auswählt, muss vor dem Klick sehen, wen er meint."""
    seed_owner(user_repo, _ACC, _OWNER)
    _seed_three(review_deps, mock_db)
    order = _list_first(review_deps, user_repo, fake_messenger)

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_freigeben", "positions": [1, 3]},
    )
    bot.handle(
        meta_text_payload("Buchung 1 und 3 freigeben", message_id="wamid.a"), _ACC
    )

    text = fake_messenger.buttons[-1][1]
    assert "Diese 2 freigeben?" in text
    assert _GUESTS[order[0]] in text
    assert _GUESTS[order[2]] in text
    assert _GUESTS[order[1]] not in text


def test_auswahl_gibt_genau_die_gewaehlten_frei(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    seed_owner(user_repo, _ACC, _OWNER)
    _seed_three(review_deps, mock_db)
    order = _list_first(review_deps, user_repo, fake_messenger)
    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_freigeben", "positions": [1, 3]},
    )
    bot.handle(
        meta_text_payload("Buchung 1 und 3 freigeben", message_id="wamid.a"), _ACC
    )
    action_id = fake_messenger.buttons[-1][2][0].id.removeprefix("confirm_")

    bot.handle(meta_button_payload(f"confirm_{action_id}"), _ACC)

    approved = review_deps.review_router.approved  # type: ignore[attr-defined]
    assert sorted(approved) == sorted([order[0], order[2]])


def test_einzelne_freigabe_bleibt_unveraendert(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    """Der Einzelfall darf nicht plötzlich wie eine Sammelfreigabe aussehen."""
    seed_owner(user_repo, _ACC, _OWNER)
    _seed_three(review_deps, mock_db)
    order = _list_first(review_deps, user_repo, fake_messenger)

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_freigeben", "positions": [2]},
    )
    bot.handle(meta_text_payload("Buchung 2 freigeben", message_id="wamid.b"), _ACC)

    text = fake_messenger.buttons[-1][1]
    assert "Freigeben?" in text
    assert "Diese" not in text
    assert _GUESTS[order[1]] in text


def test_ungueltige_nummer_bricht_die_ganze_auswahl_ab(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    """Bei "1, 3 und 9" darf nicht stillschweigend 1 und 3 durchgehen —
    sonst rätselt der Nutzer, ob die 9 dabei war."""
    seed_owner(user_repo, _ACC, _OWNER)
    _seed_three(review_deps, mock_db)

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_freigeben", "positions": [1, 3, 9]},
    )
    bot.handle(
        meta_text_payload("Buchung 1, 3 und 9 freigeben", message_id="wamid.c"), _ACC
    )

    assert not fake_messenger.buttons
    assert review_deps.review_router.approved == []  # type: ignore[attr-defined]
    assert "9" in fake_messenger.texts[-1][1]


def test_auswahl_dedupliziert_die_empfaenger(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    """Drei Buchungen derselben Wohnung → der Partner steht einmal da."""
    seed_owner(user_repo, _ACC, _OWNER)
    _seed_three(review_deps, mock_db)
    from backend.features.cleaning.models import CleaningPartner

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
        {"action": "review_freigeben", "positions": [1, 2, 3]},
    )
    bot.handle(
        meta_text_payload("Buchung 1, 2 und 3 freigeben", message_id="wamid.d"), _ACC
    )

    assert fake_messenger.buttons[-1][1].count("Dennis") == 1
