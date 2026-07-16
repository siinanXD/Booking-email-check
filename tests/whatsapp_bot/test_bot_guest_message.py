"""Die Nachricht des Gastes ist im Chat sichtbar und abrufbar.

Regression: `BookingExtraction` hatte kein Feld für den Text des Gastes, der
Extraktions-Prompt fragte ihn nicht ab. Das Anliegen existierte nirgends als
Datum — es steckte nur im Rohtext der Mail. Der Entwurf griff daraus Stichworte
auf, ohne sie als gestellte Frage zu erkennen: "sag mir, welche konkreten Fragen
du noch hast (z. B. zu Parkmöglichkeiten oder zum Preis)" — an einen Gast, der
genau danach gefragt hatte.
"""

from __future__ import annotations

from typing import Any

from backend.features.whatsapp_bot.deps import BotDeps
from backend.infrastructure.repositories.user_repository import UserRepository
from tests.whatsapp_bot.conftest import (
    FakeMessenger,
    make_bot,
    meta_text_payload,
    seed_owner,
    seed_review,
)

_ACC = "acc-1"
_OWNER = "4915711111111"
_PROP = "Münzbach Ferienzimmer"

# Wortlaut aus einer echten Airbnb-Anfrage (Gastdaten ersetzt).
_FRAGE = (
    "Hallo, ich möchte dein Zimmer buchen, aber ich habe mich über die "
    "Parkmöglichkeiten für ein Auto in der Gegend gewundert. Gibt es in der "
    "Nähe kostenlose Parkplätze?"
)


def _seed(deps: BotDeps, db: Any, cid: str, *, message: str | None) -> None:
    seed_review(
        deps,
        db,
        _ACC,
        correlation_id=cid,
        intent="guest_inquiry",
        guest="Alek",
        property_name=_PROP,
        guest_message=message,
    )


def test_nachricht_ist_abrufbar(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", message=_FRAGE)

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_nachricht", "position": 1},
    )
    bot.handle(meta_text_payload("Nachricht zu Buchung 1"), _ACC)

    text = fake_messenger.texts[-1][1]
    assert "Parkmöglichkeiten" in text
    assert "kostenlose Parkplätze" in text
    assert "Alek" in text


def test_nachricht_steht_in_den_details_vor_dem_entwurf(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    """Der Anlass gehört über die Antwort — sonst liest man sie ohne die Frage."""
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", message=_FRAGE)

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_details", "position": 1},
    )
    bot.handle(meta_text_payload("Zeig mir Buchung 1"), _ACC)

    text = fake_messenger.texts[-1][1]
    assert "Parkmöglichkeiten" in text
    assert text.index("Nachricht vom Gast") < text.index("Entwurf")


def test_ohne_nachricht_bleibt_die_karte_schlank(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    """Reine Buchungsmails haben keinen Gasttext — kein leerer Block."""
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", message=None)

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_details", "position": 1},
    )
    bot.handle(meta_text_payload("Zeig mir Buchung 1"), _ACC)

    assert "Nachricht vom Gast" not in fake_messenger.texts[-1][1]


def test_abruf_ohne_nachricht_erklaert_sich(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", message=None)

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_nachricht", "position": 1},
    )
    bot.handle(meta_text_payload("Was hat der Gast geschrieben?"), _ACC)

    assert "keine Nachricht vom Gast" in fake_messenger.texts[-1][1]


def test_langer_text_wird_gekuerzt_aber_lesbar(
    review_deps: BotDeps,
    mock_db: Any,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> None:
    """WhatsApp hat ein Textlimit — der Anfang der Frage muss stehen bleiben."""
    seed_owner(user_repo, _ACC, _OWNER)
    _seed(review_deps, mock_db, "c1", message=_FRAGE + " " + "und weiter " * 300)

    bot = make_bot(
        review_deps,
        user_repo,
        fake_messenger,
        {"action": "review_nachricht", "position": 1},
    )
    bot.handle(meta_text_payload("Nachricht zu Buchung 1"), _ACC)

    text = fake_messenger.texts[-1][1]
    assert "Parkmöglichkeiten" in text
    assert text.endswith("…")
    assert len(text) < 1200
