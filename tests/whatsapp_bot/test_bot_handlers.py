"""Tests: Lese-Handler (Putzplan, Buchungen) inkl. Tenant-Isolation."""

from __future__ import annotations

from datetime import date

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.features.cleaning.models import (
    CleaningPartner,
    CleaningTask,
    CleaningTaskStatus,
)
from backend.features.whatsapp_bot.deps import BotDeps
from backend.features.whatsapp_bot.handlers_read import (
    handle_buchung_details,
    handle_buchungen,
    handle_putzplan,
    handle_putzplan_eigene,
)
from backend.features.whatsapp_bot.models import ResolvedSender, UserIntent

_OWNER = ResolvedSender(
    account_id="acc-1", wa_id="4915711111111", name="Olaf", role="owner"
)
_CLEANER = ResolvedSender(
    account_id="acc-1",
    wa_id="4915722222222",
    name="Petra",
    role="cleaner",
    partner_id="p1",
)


def _seed_task(
    deps: BotDeps,
    *,
    account_id: str = "acc-1",
    task_id: str = "t1",
    partner_id: str | None = "p1",
    cleaning_date: date = date(2026, 7, 15),
    status: CleaningTaskStatus = CleaningTaskStatus.SCHEDULED,
) -> None:
    deps.cleaning_task_repo.upsert(
        CleaningTask(
            task_id=task_id,
            account_id=account_id,
            property_name="FeWo Seeblick",
            guest_name="Max",
            cleaning_date=cleaning_date,
            partner_id=partner_id,
            status=status,
        )
    )


def _intent(start: date, end: date) -> UserIntent:
    return UserIntent(zeitraum_start=start, zeitraum_ende=end)


def test_putzplan_mit_excel_anhang(bot_deps: BotDeps) -> None:
    _seed_task(bot_deps)
    bot_deps.cleaning_partner_repo.upsert(
        CleaningPartner(partner_id="p1", name="Petra"), account_id="acc-1"
    )
    result = handle_putzplan(
        bot_deps, _OWNER, _intent(date(2026, 7, 13), date(2026, 7, 19))
    )
    assert "*1 Reinigungen*" in result.reply.text
    assert result.reply.document is not None
    assert result.reply.document.filename == "Putzplan_KW29.xlsx"
    assert result.reply.document.content[:2] == b"PK"  # XLSX = ZIP


def test_putzplan_leer_ohne_anhang(bot_deps: BotDeps) -> None:
    result = handle_putzplan(
        bot_deps, _OWNER, _intent(date(2026, 7, 13), date(2026, 7, 19))
    )
    assert "Keine Reinigungen" in result.reply.text
    assert result.reply.document is None


def test_putzplan_tenant_isolation(bot_deps: BotDeps) -> None:
    """Aufträge von Tenant B erscheinen nie im Plan von Tenant A."""
    _seed_task(bot_deps, account_id="acc-2", task_id="fremd")
    result = handle_putzplan(
        bot_deps, _OWNER, _intent(date(2026, 7, 13), date(2026, 7, 19))
    )
    assert "Keine Reinigungen" in result.reply.text


def test_putzplan_stornierte_ausgeblendet(bot_deps: BotDeps) -> None:
    _seed_task(bot_deps, status=CleaningTaskStatus.CANCELLED)
    result = handle_putzplan(
        bot_deps, _OWNER, _intent(date(2026, 7, 13), date(2026, 7, 19))
    )
    assert "Keine Reinigungen" in result.reply.text


def test_eigene_termine_nur_eigener_partner(bot_deps: BotDeps) -> None:
    _seed_task(bot_deps, task_id="mein", partner_id="p1")
    _seed_task(bot_deps, task_id="fremd", partner_id="p2")
    result = handle_putzplan_eigene(
        bot_deps, _CLEANER, _intent(date(2026, 7, 13), date(2026, 7, 19))
    )
    assert result.reply.text.count("\U0001f9fd") == 1


def _seed_booking(
    deps: BotDeps,
    *,
    account_id: str = "acc-1",
    cid: str = "c1",
    booking_number: str = "AB123",
    check_in: date = date(2026, 7, 14),
) -> None:
    deps.extraction_repo.save(
        cid,
        f"msg-{cid}",
        BookingExtraction(
            intent="new_booking",
            guest_name="Max Mustermann",
            booking_number=booking_number,
            property_name="FeWo Seeblick",
            check_in=check_in,
            check_out=date(2026, 7, 18),
            price=450.0,
            platform="Booking.com",
        ),
        account_id=account_id,
    )


def test_buchungen_liste(bot_deps: BotDeps) -> None:
    _seed_booking(bot_deps)
    result = handle_buchungen(
        bot_deps, _OWNER, _intent(date(2026, 7, 13), date(2026, 7, 19))
    )
    assert "Max Mustermann" in result.reply.text
    assert "FeWo Seeblick" in result.reply.text


def test_buchungen_tenant_isolation(bot_deps: BotDeps) -> None:
    _seed_booking(bot_deps, account_id="acc-2", cid="fremd")
    result = handle_buchungen(
        bot_deps, _OWNER, _intent(date(2026, 7, 13), date(2026, 7, 19))
    )
    assert "Max Mustermann" not in result.reply.text
    assert "Keine Buchungen" in result.reply.text


def test_buchung_details(bot_deps: BotDeps) -> None:
    _seed_booking(bot_deps)
    intent = UserIntent(booking_ref="AB123")
    result = handle_buchung_details(bot_deps, _OWNER, intent)
    assert "*Buchung AB123*" in result.reply.text
    assert "450.00 €" in result.reply.text
    assert "Booking.com" in result.reply.text


def test_buchung_details_ohne_ref_rueckfrage(bot_deps: BotDeps) -> None:
    result = handle_buchung_details(bot_deps, _OWNER, UserIntent())
    assert "Buchungsnummer" in result.reply.text
    assert "Namen des Gastes" in result.reply.text


def test_buchung_details_ueber_gastnamen(bot_deps: BotDeps) -> None:
    """Der Kunde gleicht mit einem System ab, in dem die Nummer fehlt."""
    _seed_booking(bot_deps)
    result = handle_buchung_details(
        bot_deps, _OWNER, UserIntent(person_name="Max Mustermann")
    )
    assert "*Buchung AB123*" in result.reply.text
    assert "Booking.com" in result.reply.text


def test_buchung_details_gastname_teiltreffer(bot_deps: BotDeps) -> None:
    """Nachname genügt, Groß/Kleinschreibung egal."""
    _seed_booking(bot_deps)
    result = handle_buchung_details(
        bot_deps, _OWNER, UserIntent(person_name="mustermann")
    )
    assert "*Buchung AB123*" in result.reply.text


def test_buchung_details_gastname_mehrdeutig_listet_auf(bot_deps: BotDeps) -> None:
    """Zwei Buchungen desselben Gastes: auflisten statt willkürlich wählen."""
    _seed_booking(bot_deps, cid="c1", booking_number="AB123")
    _seed_booking(bot_deps, cid="c2", booking_number="AB124")
    result = handle_buchung_details(
        bot_deps, _OWNER, UserIntent(person_name="Max Mustermann")
    )
    assert "2 Buchungen" in result.reply.text
    assert "AB123" in result.reply.text
    assert "AB124" in result.reply.text


def test_buchung_details_gastname_unbekannt(bot_deps: BotDeps) -> None:
    _seed_booking(bot_deps)
    result = handle_buchung_details(bot_deps, _OWNER, UserIntent(person_name="Niemand"))
    assert "keine Buchung" in result.reply.text


def test_buchung_details_gastname_tenant_isolation(bot_deps: BotDeps) -> None:
    _seed_booking(bot_deps, account_id="acc-2", cid="fremd")
    result = handle_buchung_details(
        bot_deps, _OWNER, UserIntent(person_name="Max Mustermann")
    )
    assert "keine Buchung" in result.reply.text


def test_gastname_wird_nicht_als_regex_ausgewertet(bot_deps: BotDeps) -> None:
    """Nutzereingabe ist Wert, nie Ausdruck — sonst matcht ".*" alles."""
    _seed_booking(bot_deps)
    result = handle_buchung_details(bot_deps, _OWNER, UserIntent(person_name=".*"))
    assert "keine Buchung" in result.reply.text


def test_buchung_details_fremder_tenant_nicht_sichtbar(bot_deps: BotDeps) -> None:
    _seed_booking(bot_deps, account_id="acc-2", cid="fremd")
    intent = UserIntent(booking_ref="AB123")
    result = handle_buchung_details(bot_deps, _OWNER, intent)
    assert "keine Buchung" in result.reply.text
