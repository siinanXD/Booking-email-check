"""Lese-Handler: Putzplan (mit Excel) und Buchungsanzeige."""

from __future__ import annotations

from datetime import date, timedelta

from backend.features.cleaning.export import build_cleaning_xlsx
from backend.features.whatsapp_bot import messages
from backend.features.whatsapp_bot.dates import format_date, today_in_tz
from backend.features.whatsapp_bot.deps import BotDeps, HandlerResult
from backend.features.whatsapp_bot.models import (
    BotDocument,
    BotReply,
    ResolvedSender,
    UserIntent,
)

_DEFAULT_RANGE_DAYS = 7


def _effective_period(intent: UserIntent, deps: BotDeps) -> tuple[date, date]:
    if intent.zeitraum_start and intent.zeitraum_ende:
        return intent.zeitraum_start, intent.zeitraum_ende
    start = today_in_tz(deps.timezone)
    return start, start + timedelta(days=_DEFAULT_RANGE_DAYS - 1)


def handle_putzplan(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Putzplan für den Zeitraum: Zusammenfassung + Excel-Anhang."""
    start, end = _effective_period(intent, deps)
    tasks = deps.cleaning_task_repo.list_tasks(
        account_id=sender.account_id,
        property_name=intent.property_name,
        date_from=start,
        date_to=end,
    )
    tasks = [t for t in tasks if t.status.value != "cancelled"]
    summary = messages.putzplan_summary(tasks, start=start, end=end)
    if not tasks:
        return HandlerResult(reply=BotReply.message(summary))

    partners = deps.cleaning_partner_repo.list_partners(account_id=sender.account_id)
    partners_by_id = {p.partner_id: p for p in partners}
    listing = messages.putzplan_tasks_list(tasks, partners_by_id)
    xlsx = build_cleaning_xlsx(tasks, partners_by_id)
    week = start.isocalendar()[1]
    document = BotDocument(filename=f"Putzplan_KW{week}.xlsx", content=xlsx)
    return HandlerResult(
        reply=BotReply(text=f"{summary}\n\n{listing}", document=document)
    )


def handle_putzplan_eigene(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Eigene Termine einer Reinigungskraft (nur deren Aufträge)."""
    start, end = _effective_period(intent, deps)
    tasks = deps.cleaning_task_repo.list_tasks(
        account_id=sender.account_id,
        date_from=start,
        date_to=end,
    )
    if sender.partner_id:
        tasks = [t for t in tasks if t.partner_id == sender.partner_id]
    tasks = [t for t in tasks if t.status.value != "cancelled"]
    if not tasks:
        text = (
            f"\U0001f9f9 *Deine Termine {format_date(start)} – {format_date(end)}*"
            "\n\nKeine Termine in diesem Zeitraum. \U0001f389"
        )
        return HandlerResult(reply=BotReply.message(text))
    lines = [f"\U0001f9f9 *Deine Termine {format_date(start)} – {format_date(end)}*\n"]
    for task in tasks[:10]:
        note = f"\n   \U0001f4dd {task.note}" if task.note else ""
        lines.append(
            f"\U0001f9fd {format_date(task.cleaning_date)} "
            f"*{task.property_name or '—'}*{note}"
        )
    if len(tasks) > 10:
        lines.append(f"… und {len(tasks) - 10} weitere")
    return HandlerResult(reply=BotReply.message("\n".join(lines)))


def handle_buchungen(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Buchungsliste im Zeitraum."""
    start, end = _effective_period(intent, deps)
    bookings = deps.extraction_repo.list_bookings_between(
        account_id=sender.account_id,
        date_from=start,
        date_to=end,
    )
    rows = []
    for _cid, extraction in bookings:
        if intent.property_name and (
            (extraction.property_name or "").strip().lower()
            != intent.property_name.strip().lower()
        ):
            continue
        rows.append(
            (
                extraction.booking_number or "",
                extraction.guest_name or "Unbekannt",
                extraction.check_in,
                extraction.check_out,
                extraction.property_name,
            )
        )
    text = messages.bookings_list(rows, start=start, end=end)
    return HandlerResult(reply=BotReply.message(text))


def handle_buchung_details(
    deps: BotDeps, sender: ResolvedSender, intent: UserIntent
) -> HandlerResult:
    """Detailkarte einer Buchung anhand der Buchungsnummer."""
    if not intent.booking_ref:
        return HandlerResult(
            reply=BotReply.message(
                messages.clarification(
                    "Welche Buchung meinst du? Bitte nenn mir die Buchungsnummer."
                )
            )
        )
    extraction = deps.extraction_repo.find_booking_by_number(
        intent.booking_ref, account_id=sender.account_id
    )
    if extraction is None:
        return HandlerResult(
            reply=BotReply.message(
                messages.clarification(
                    f"Ich habe keine Buchung *{intent.booking_ref}* gefunden."
                )
            )
        )
    text = messages.booking_details(
        ref=extraction.booking_number or intent.booking_ref,
        guest_name=extraction.guest_name or "Unbekannt",
        property_name=extraction.property_name or "—",
        check_in=extraction.check_in,
        check_out=extraction.check_out,
        price=extraction.price,
        platform=extraction.platform or extraction.channel,
    )
    return HandlerResult(reply=BotReply.message(text))
