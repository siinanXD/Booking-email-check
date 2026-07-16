"""Infotext für den Putzplan bei der Freigabe.

`CleaningTask.note` existierte samt Excel-Spalte "Bemerkung" und ICS-Beschreibung,
war aber nur über die Weboberfläche pflegbar. Wer per Chat freigibt, musste für
einen Satz an die Putzkraft extra ins Dashboard.

Der Text kommt im Befehl mit ("Buchung 1 freigeben, Notiz: Schlüssel beim
Nachbarn") — kein zusätzlicher Dialogschritt, und er kombiniert sich mit der
Mehrfach-Auswahl.
"""

from __future__ import annotations

from typing import Any

from backend.features.cleaning.models import CleaningTask, CleaningTaskStatus
from backend.features.whatsapp_bot.deps import BotDeps
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
_NOTE = "Schlüssel liegt beim Nachbarn"


def _seed(deps: BotDeps, db: Any, cid: str, guest: str, *, with_task: bool) -> None:
    seed_review(
        deps,
        db,
        _ACC,
        correlation_id=cid,
        intent="new_booking",
        guest=guest,
        property_name=_PROP,
    )
    if with_task:
        deps.cleaning_task_repo.upsert(
            CleaningTask(
                task_id=f"t-{cid}",
                account_id=_ACC,
                correlation_id=cid,
                property_name=_PROP,
                guest_name=guest,
                status=CleaningTaskStatus.SCHEDULED,
            ),
            account_id=_ACC,
        )


def _approve(
    deps: BotDeps,
    user_repo: UserRepository,
    messenger: FakeMessenger,
    payload: dict[str, Any],
    text: str,
) -> None:
    bot = make_bot(deps, user_repo, messenger, payload)
    bot.handle(meta_text_payload(text, message_id="wamid.cmd"), _ACC)
    action_id = messenger.buttons[-1][2][0].id.removeprefix("confirm_")
    bot.handle(meta_button_payload(f"confirm_{action_id}"), _ACC)


def test_infotext_landet_am_putzauftrag(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "Coosemans", with_task=True)

    _approve(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_freigeben", "positions": [1], "notiz": _NOTE},
        f"Buchung 1 freigeben, Notiz: {_NOTE}",
    )

    task = review_deps.cleaning_task_repo.find_by_correlation_id("c1", account_id=_ACC)
    assert task is not None
    assert task.note == _NOTE
    assert "Infotext steht im Putzplan" in fake_messenger.texts[-1][1]


def test_infotext_steht_vor_dem_klick_im_dialog(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    """Er landet in Excel und Kalender — man muss ihn vorher sehen."""
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "Coosemans", with_task=True)

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_freigeben", "positions": [1], "notiz": _NOTE},
    )
    bot.handle(
        meta_text_payload("Buchung 1 freigeben, Notiz: …", message_id="w.1"), _ACC
    )

    assert _NOTE in fake_messenger.buttons[-1][1]


def test_ohne_infotext_bleibt_alles_wie_bisher(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    """Keine Notiz → kein Notiz-Block, keine Notiz-Meldung."""
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "Coosemans", with_task=True)

    _approve(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_freigeben", "positions": [1]},
        "Buchung 1 freigeben",
    )

    task = review_deps.cleaning_task_repo.find_by_correlation_id("c1", account_id=_ACC)
    assert task is not None and task.note is None
    assert "Infotext" not in fake_messenger.texts[-1][1]


def test_ohne_putzauftrag_wird_der_verlust_gemeldet(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    """Den Text still verschlucken wäre schlimmer als die Warnung."""
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "Coosemans", with_task=False)

    _approve(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_freigeben", "positions": [1], "notiz": _NOTE},
        f"Buchung 1 freigeben, Notiz: {_NOTE}",
    )

    text = fake_messenger.texts[-1][1]
    assert "1 Eintrag freigegeben" in text
    assert "konnte nirgends hinterlegt werden" in text


def test_infotext_gilt_fuer_die_ganze_auswahl(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    """Bei "1 und 2 freigeben, Notiz: …" bekommt jeder Auftrag den Text."""
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "Coosemans", with_task=True)
    _seed(review_deps, mock_db, "c2", "Jutta", with_task=True)

    _approve(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_freigeben", "positions": [1, 2], "notiz": _NOTE},
        f"Buchung 1 und 2 freigeben, Notiz: {_NOTE}",
    )

    notes = [
        review_deps.cleaning_task_repo.find_by_correlation_id(cid, account_id=_ACC)
        for cid in ("c1", "c2")
    ]
    assert [t.note for t in notes if t] == [_NOTE, _NOTE]


def test_infotext_ueberlebt_eine_folgemail(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    """`manually_edited` schützt die bewusste Anweisung des Gastgebers."""
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", "Coosemans", with_task=True)

    _approve(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_freigeben", "positions": [1], "notiz": _NOTE},
        f"Buchung 1 freigeben, Notiz: {_NOTE}",
    )

    task = review_deps.cleaning_task_repo.find_by_correlation_id("c1", account_id=_ACC)
    assert task is not None
    assert task.manually_edited is True
