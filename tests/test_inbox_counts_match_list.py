"""Posteingang: Zähler und Liste müssen dieselbe Frage beantworten.

Regression: Die Nav-Badges klassifizierten bei jedem Request live in Python, die
Liste filterte auf die vorberechneten Felder `is_booking`/`effective_intent`.
Zwei Codepfade für dieselbe Frage — sie liefen auseinander. Im Bestand zeigte der
Posteingang "Nachrichten: 1" und "Änderungen: 1", ohne dass sich die Einträge
öffnen ließen: 22 von 49 Mails hatten die Felder gar nicht und waren für die
Liste unsichtbar, wurden vom Zähler aber mitgezählt.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.models.email import StoredEmail
from backend.infrastructure.repositories.email_repository import EmailRepository
from backend.infrastructure.repositories.mongo import Db

ACCOUNT = "acc-1"
_NOW = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)
_WINDOW = (_NOW - timedelta(days=30)).isoformat()


def _seed(
    repo: EmailRepository,
    db: Db,
    cid: str,
    *,
    intent: str | None,
    is_booking: bool | None,
    days_ago: int = 1,
) -> None:
    """Legt eine Mail an; ``is_booking=None`` lässt die Felder ganz weg."""
    repo.upsert_by_message_id(
        StoredEmail(
            message_id=f"m-{cid}",
            from_address="bookings@beds24.com",
            subject=f"Buchung {cid}",
            body_text="…",
            received_at=_NOW - timedelta(days=days_ago),
            correlation_id=cid,
            account_id=ACCOUNT,
        )
    )
    if is_booking is None:
        return
    db["emails"].update_one(
        {"correlation_id": cid},
        {"$set": {"is_booking": is_booking, "effective_intent": intent}},
    )


def _counts(repo: EmailRepository) -> dict[str, int]:
    return repo.count_booking_intents(account_id=ACCOUNT, received_since=_WINDOW)


def _listed(repo: EmailRepository, intent: str) -> int:
    _, total = repo.list_filtered(
        account_id=ACCOUNT,
        intent=intent,
        booking_related=True,
        received_since=_WINDOW,
    )
    return total


def test_zaehler_und_liste_stimmen_ueberein(mock_db: Db) -> None:
    repo = EmailRepository(mock_db)
    _seed(repo, mock_db, "c1", intent="new_booking", is_booking=True)
    _seed(repo, mock_db, "c2", intent="new_booking", is_booking=True)
    _seed(repo, mock_db, "c3", intent="guest_inquiry", is_booking=True)

    counts = _counts(repo)

    assert counts[BookingIntent.NEW_BOOKING.value] == _listed(repo, "new_booking") == 2
    assert (
        counts[BookingIntent.GUEST_INQUIRY.value] == _listed(repo, "guest_inquiry") == 1
    )


def test_mail_ohne_vorberechnete_felder_wird_nicht_gezaehlt(mock_db: Db) -> None:
    """Der Kern des Fehlers: gezählt, aber unauffindbar.

    Solche Mails gehören ins Backfill (scripts/backfill_booking_relevance.py) —
    der Zähler darf sie nicht vortäuschen, solange die Liste sie nicht findet.
    """
    repo = EmailRepository(mock_db)
    _seed(repo, mock_db, "c1", intent=None, is_booking=None)

    assert _counts(repo) == {}
    assert _listed(repo, "guest_inquiry") == 0


def test_keine_buchung_zaehlt_nicht(mock_db: Db) -> None:
    repo = EmailRepository(mock_db)
    _seed(repo, mock_db, "c1", intent="other", is_booking=False)

    assert _counts(repo) == {}


def test_ausserhalb_des_fensters_zaehlt_nicht(mock_db: Db) -> None:
    """Das Fenster muss dasselbe sein wie in der Liste — sonst driftet es wieder."""
    repo = EmailRepository(mock_db)
    _seed(repo, mock_db, "c1", intent="new_booking", is_booking=True, days_ago=40)

    assert _counts(repo) == {}
    assert _listed(repo, "new_booking") == 0


def test_fremder_mandant_zaehlt_nicht(mock_db: Db) -> None:
    repo = EmailRepository(mock_db)
    _seed(repo, mock_db, "c1", intent="new_booking", is_booking=True)

    assert repo.count_booking_intents(account_id="acc-2", received_since=_WINDOW) == {}


def test_beschwerden_sind_ueber_den_nachrichten_tab_auffindbar(mock_db: Db) -> None:
    """nav_messages zählt guest_inquiry + complaint; einen Beschwerden-Tab gibt
    es nicht. Der Nachrichten-Tab muss deshalb beide Intents filtern."""
    repo = EmailRepository(mock_db)
    _seed(repo, mock_db, "c1", intent="guest_inquiry", is_booking=True)
    _seed(repo, mock_db, "c2", intent="complaint", is_booking=True)

    counts = _counts(repo)
    nav_messages = counts.get("guest_inquiry", 0) + counts.get("complaint", 0)
    _, listed = repo.list_filtered(
        account_id=ACCOUNT,
        intents=["guest_inquiry", "complaint"],
        booking_related=True,
        received_since=_WINDOW,
    )

    assert nav_messages == listed == 2
