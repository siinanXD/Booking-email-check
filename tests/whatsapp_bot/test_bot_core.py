"""Tests: Rollen-Matrix, Datums-Auflösung, Button-IDs, Sender-Auflösung."""

from __future__ import annotations

from datetime import date

from backend.features.cleaning.models import CleaningPartner
from backend.features.whatsapp_bot.dates import (
    is_calendar_week,
    period_heading,
    period_slug,
    resolve_period,
)
from backend.features.whatsapp_bot.deps import BotDeps
from backend.features.whatsapp_bot.messages_putzplan import putzplan_summary
from backend.features.whatsapp_bot.models import BotAction, parse_button_id
from backend.features.whatsapp_bot.permissions import is_allowed
from backend.features.whatsapp_bot.sender_resolver import SenderResolver
from backend.infrastructure.repositories.user_repository import UserRepository

_TODAY = date(2026, 7, 8)  # Mittwoch, KW 28


# --- Rollen-Matrix (vollständig laut Spec) ---------------------------------

_MATRIX_CASES = [
    (BotAction.PUTZPLAN_ERSTELLEN, True, True, False),
    (BotAction.PUTZPLAN_EIGENER_ABRUF, True, True, True),
    (BotAction.BUCHUNGEN_ANZEIGEN, True, True, False),
    (BotAction.BUCHUNG_DETAILS, True, True, False),
    (BotAction.MITARBEITER_LISTE, True, True, False),
    (BotAction.OBJEKT_LISTE, True, True, False),
    # Gastnachrichten sind Review-Inhalt: lesen dürfen Owner und Manager.
    (BotAction.REVIEW_NACHRICHT, True, True, False),
    # Ändern darf ausschließlich der Owner.
    (BotAction.MITARBEITER_ANLEGEN, True, False, False),
    (BotAction.MITARBEITER_BEARBEITEN, True, False, False),
    (BotAction.MITARBEITER_AENDERN, True, False, False),
    (BotAction.OBJEKT_ANLEGEN, True, False, False),
    (BotAction.OBJEKT_ZUWEISEN, True, False, False),
    (BotAction.OBJEKT_ENTZIEHEN, True, False, False),
    (BotAction.OBJEKT_BEARBEITEN, True, False, False),
    (BotAction.OBJEKT_LOESCHEN, True, False, False),
    (BotAction.HILFE, True, True, True),
]


def test_role_matrix_complete() -> None:
    for action, owner, manager, cleaner in _MATRIX_CASES:
        assert is_allowed("owner", action) is owner, action
        assert is_allowed("manager", action) is manager, action
        assert is_allowed("cleaner", action) is cleaner, action


def test_jede_aktion_ist_in_der_matrix() -> None:
    """Kein Intent darf ohne Rollen-Eintrag durchrutschen."""
    for action in BotAction:
        assert any(
            is_allowed(role, action) for role in ("owner", "manager", "cleaner")
        ), action


def test_cleaner_darf_ausschliesslich_putzplan() -> None:
    erlaubt = {action for action in BotAction if is_allowed("cleaner", action)}
    assert erlaubt == {
        BotAction.PUTZPLAN_EIGENER_ABRUF,
        BotAction.HILFE,
        BotAction.UNKLAR,
    }


# --- Deterministische Datums-Auflösung --------------------------------------


def test_resolve_heute_und_morgen() -> None:
    assert resolve_period("heute", today=_TODAY) == (_TODAY, _TODAY)
    tomorrow = date(2026, 7, 9)
    assert resolve_period("morgen bitte", today=_TODAY) == (tomorrow, tomorrow)


def test_resolve_naechste_woche() -> None:
    start, end = resolve_period("nächste Woche", today=_TODAY)  # type: ignore[misc]
    assert start == date(2026, 7, 13)
    assert end == date(2026, 7, 19)
    assert start.weekday() == 0 and end.weekday() == 6


def test_resolve_kalenderwoche() -> None:
    start, end = resolve_period("KW 32", today=_TODAY)  # type: ignore[misc]
    assert start.isocalendar()[1] == 32
    assert (end - start).days == 6


def test_resolve_kw_in_vergangenheit_rutscht_ins_naechste_jahr() -> None:
    start, _ = resolve_period("KW 2", today=_TODAY)  # type: ignore[misc]
    assert start.year == 2027


def test_resolve_explizite_daten_als_bereich() -> None:
    start, end = resolve_period("vom 12.08. bis 15.08.", today=_TODAY)  # type: ignore[misc]
    assert start == date(2026, 8, 12)
    assert end == date(2026, 8, 15)


def test_resolve_vergangenes_datum_ohne_jahr_naechstes_jahr() -> None:
    start, end = resolve_period("01.02.", today=_TODAY)  # type: ignore[misc]
    assert start == date(2027, 2, 1) and end == start


def test_resolve_bereich_ohne_schlusspunkt() -> None:
    """ "24.07" ohne Schlusspunkt fiel früher weg — der Bereich schrumpfte."""
    start, end = resolve_period(  # type: ignore[misc]
        "Gibt es Buchungen in dem Zeitraum von 24.07 - 27.07.2026", today=_TODAY
    )
    assert start == date(2026, 7, 24)
    assert end == date(2026, 7, 27)


def test_resolve_jahr_wird_vom_partner_datum_geerbt() -> None:
    start, end = resolve_period("vom 24.07 bis 27.07.2027", today=_TODAY)  # type: ignore[misc]
    assert start == date(2027, 7, 24)
    assert end == date(2027, 7, 27)


def test_resolve_bereich_ueber_jahreswechsel() -> None:
    start, end = resolve_period("28.12 - 03.01.2027", today=_TODAY)  # type: ignore[misc]
    assert start == date(2026, 12, 28)
    assert end == date(2027, 1, 3)


def test_resolve_uhrzeit_ist_kein_datum() -> None:
    assert resolve_period("wir treffen uns um 12.08 Uhr", today=_TODAY) is None


def test_resolve_verdrehter_bereich_wird_sortiert() -> None:
    start, end = resolve_period("vom 15.08. bis 12.08.", today=_TODAY)  # type: ignore[misc]
    assert start == date(2026, 8, 12)
    assert end == date(2026, 8, 15)


def test_kw_label_nur_fuer_echte_kalenderwochen() -> None:
    """Ein rollierendes 7-Tage-Fenster darf keine KW-Nummer tragen.

    Fragte jemand sonntags, stand "KW 29" über einem Bereich, der zu sechs
    Siebteln in KW 30 lag — Abreisen am Fensterrand wirkten dadurch verschluckt.
    """
    sonntag, plus6 = date(2026, 7, 19), date(2026, 7, 25)
    assert not is_calendar_week(sonntag, plus6)
    assert period_heading(sonntag, plus6) == "19.07.2026 – 25.07.2026"

    montag, sonntag_30 = date(2026, 7, 20), date(2026, 7, 26)
    assert is_calendar_week(montag, sonntag_30)
    assert period_heading(montag, sonntag_30) == "KW 30"


def test_putzplan_dateiname_folgt_dem_zeitraum() -> None:
    assert period_slug(date(2026, 7, 20), date(2026, 7, 26)) == "KW30"
    assert period_slug(date(2026, 7, 19), date(2026, 7, 25)) == "19-07_bis_25-07-2026"


def test_putzplan_summary_nennt_das_kriterium() -> None:
    """Ohne "nach Abreise" wirken Buchungen am Rand wie verschluckt."""
    text = putzplan_summary([], start=date(2026, 7, 19), end=date(2026, 7, 25))
    assert "nach Abreise" in text
    assert "KW" not in text  # kein falsches Kalenderwochen-Label


def test_resolve_unbekanntes_liefert_none() -> None:
    assert resolve_period("irgendwann demnächst mal", today=_TODAY) is None
    assert resolve_period(None, today=_TODAY) is None


# --- Button-ID-Routing (deterministisch, ohne LLM) --------------------------


def test_parse_button_id() -> None:
    assert parse_button_id("confirm_abc123") == ("confirm", "abc123")
    assert parse_button_id("cancel_abc123") == ("cancel", "abc123")
    assert parse_button_id("edit_abc123") is None
    assert parse_button_id("confirm_") is None
    assert parse_button_id("") is None


# --- Sender-Auflösung + Tenant-Isolation ------------------------------------


def _seed_owner(user_repo: UserRepository, account_id: str, phone: str) -> None:
    user = user_repo.create(
        f"owner-{account_id}@test.local",
        "hash",
        account_id=account_id,
        role="owner",
        first_name="Olaf",
        last_name="Owner",
    )
    user_repo.update_whatsapp_profile(
        user.id, whatsapp_phone_e164=phone, whatsapp_enabled=True
    )


def test_resolver_findet_owner(bot_deps: BotDeps, user_repo: UserRepository) -> None:
    _seed_owner(user_repo, "acc-1", "+4915711111111")
    resolver = SenderResolver(user_repo, bot_deps.cleaning_partner_repo)
    sender = resolver.resolve("4915711111111", account_id="acc-1")
    assert sender is not None
    assert sender.role == "owner"
    assert sender.name == "Olaf Owner"


def test_resolver_findet_cleaner_via_putzpartner(
    bot_deps: BotDeps, user_repo: UserRepository
) -> None:
    bot_deps.cleaning_partner_repo.upsert(
        CleaningPartner(partner_id="p1", name="Petra Putz", phone="+4915722222222"),
        account_id="acc-1",
    )
    resolver = SenderResolver(user_repo, bot_deps.cleaning_partner_repo)
    sender = resolver.resolve("4915722222222", account_id="acc-1")
    assert sender is not None
    assert sender.role == "cleaner"
    assert sender.partner_id == "p1"


def test_resolver_tenant_isolation(
    bot_deps: BotDeps, user_repo: UserRepository
) -> None:
    """Nummer aus Tenant A darf in Tenant B NICHT aufgelöst werden."""
    _seed_owner(user_repo, "acc-a", "+4915711111111")
    bot_deps.cleaning_partner_repo.upsert(
        CleaningPartner(partner_id="p1", name="Petra", phone="+4915722222222"),
        account_id="acc-a",
    )
    resolver = SenderResolver(user_repo, bot_deps.cleaning_partner_repo)
    assert resolver.resolve("4915711111111", account_id="acc-b") is None
    assert resolver.resolve("4915722222222", account_id="acc-b") is None


def test_resolver_unbekannte_nummer(
    bot_deps: BotDeps, user_repo: UserRepository
) -> None:
    resolver = SenderResolver(user_repo, bot_deps.cleaning_partner_repo)
    assert resolver.resolve("4915799999999", account_id="acc-1") is None
