"""Geplante Wochen-Berichte per WhatsApp: Putzplan (Mo) und Review (Fr).

Versand als Session-Nachricht; scheitert diese (24h-Fenster zu), greift
optional ein konfiguriertes Meta-Template als Anklopfer. Dedupe über
`whatsapp_report_markers` — genau ein Versand pro Account und Woche.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.core.config.settings import Settings
from backend.core.models.notification import WhatsAppTemplateMessage
from backend.features.cleaning.export import build_cleaning_xlsx
from backend.features.notifications.whatsapp_client import MetaCloudWhatsAppClient
from backend.features.platform.effective_settings import merge_platform_settings
from backend.features.whatsapp_bot.dates import DEFAULT_TIMEZONE, format_date
from backend.features.whatsapp_bot.messenger import BotMessenger, MetaBotMessenger
from backend.features.whatsapp_bot.models import BotDocument
from backend.features.whatsapp_bot.sender_resolver import normalize_wa_id

logger = logging.getLogger(__name__)

JOB_PUTZPLAN = "weekly_putzplan"
JOB_REVIEW = "weekly_review"


def _week_bounds(anchor: date) -> tuple[date, date]:
    start = anchor - timedelta(days=anchor.weekday())
    return start, start + timedelta(days=6)


def build_weekly_review(
    bookings: list[BookingExtraction],
    *,
    start: date,
    end: date,
    cleanings_done: int = 0,
) -> str:
    """Wochen-Review: vermietete Tage, An-/Abreisen, Umsatz, Top-Objekt."""
    nights = 0
    nights_per_property: dict[str, int] = {}
    arrivals = 0
    departures = 0
    revenue = 0.0
    for booking in bookings:
        check_in, check_out = booking.check_in, booking.check_out
        if check_in and check_out:
            overlap_start = max(check_in, start)
            overlap_end = min(check_out, end + timedelta(days=1))
            overlap = max((overlap_end - overlap_start).days, 0)
            nights += overlap
            if booking.property_name and overlap:
                key = booking.property_name
                nights_per_property[key] = nights_per_property.get(key, 0) + overlap
        if check_in and start <= check_in <= end:
            arrivals += 1
            if booking.price:
                revenue += booking.price
        if check_out and start <= check_out <= end:
            departures += 1

    week = start.isocalendar()[1]
    lines = [
        f"\U0001f4ca *Wochen-Review KW {week}*",
        f"\U0001f4c6 {format_date(start)} – {format_date(end)}",
        "",
        f"\U0001f6cf\ufe0f *{nights} Übernachtungen* vermietet",
        f"\U0001f6ec {arrivals} Anreisen \u00b7 \U0001f6eb {departures} Abreisen",
        f"\U0001f4b6 Umsatz: *{revenue:,.2f} €* (Anreisen dieser Woche)",
    ]
    if nights_per_property:
        top = max(nights_per_property.items(), key=lambda kv: kv[1])
        lines.append(f"\U0001f3e0 Meistgebucht: *{top[0]}* ({top[1]} Nächte)")
    if cleanings_done:
        lines.append(f"\U0001f9f9 {cleanings_done} Reinigungen erledigt")
    if not bookings:
        lines.append("\nKeine Buchungen in dieser Woche.")
    return "\n".join(lines)


class WeeklyReportService:
    """Versendet fällige Wochen-Berichte für alle aktiven Mandanten."""

    def __init__(
        self,
        *,
        account_repo: Any,
        platform_settings_repo: Any,
        user_repo: Any,
        extraction_repo: Any,
        cleaning_task_repo: Any,
        cleaning_partner_repo: Any,
        marker_repo: Any,
        settings: Settings,
        messenger_factory: Callable[[Settings], BotMessenger] | None = None,
        template_sender: (
            Callable[[Settings, WhatsAppTemplateMessage], bool] | None
        ) = None,
    ) -> None:
        """Initialize with repositories und Versand-Fabriken (mockbar)."""
        self._account_repo = account_repo
        self._platform_settings_repo = platform_settings_repo
        self._user_repo = user_repo
        self._extraction_repo = extraction_repo
        self._task_repo = cleaning_task_repo
        self._partner_repo = cleaning_partner_repo
        self._marker_repo = marker_repo
        self._settings = settings
        self._messenger_factory = messenger_factory or _default_messenger
        self._template_sender = template_sender or _default_template_sender

    def run_due(self, now: datetime | None = None) -> int:
        """Prüft Fälligkeit (Wochentag/Uhrzeit) und versendet; Anzahl Sendungen."""
        cfg = self._settings
        local_now = (now or datetime.now(ZoneInfo(DEFAULT_TIMEZONE))).astimezone(
            ZoneInfo(DEFAULT_TIMEZONE)
        )
        sent = 0
        if (
            cfg.whatsapp_weekly_putzplan_enabled
            and local_now.weekday() == cfg.whatsapp_weekly_putzplan_weekday
            and local_now.hour >= cfg.whatsapp_weekly_putzplan_hour
        ):
            sent += self._run_job(JOB_PUTZPLAN, local_now.date())
        if (
            cfg.whatsapp_weekly_review_enabled
            and local_now.weekday() == cfg.whatsapp_weekly_review_weekday
            and local_now.hour >= cfg.whatsapp_weekly_review_hour
        ):
            sent += self._run_job(JOB_REVIEW, local_now.date())
        return sent

    def _run_job(self, job: str, today: date) -> int:
        iso = today.isocalendar()
        period_key = f"{iso[0]}-W{iso[1]:02d}"
        sent = 0
        for account in self._account_repo.list_by_status("active"):
            recipients = self._user_repo.list_whatsapp_recipient_phones(account.id)
            if not recipients:
                continue
            effective = merge_platform_settings(
                self._settings, self._platform_settings_repo.get(account.id)
            )
            if not (
                effective.whatsapp_access_token.strip()
                and effective.whatsapp_phone_number_id.strip()
            ):
                continue
            if not self._marker_repo.try_claim(
                account_id=account.id, job=job, period_key=period_key
            ):
                continue
            try:
                if job == JOB_PUTZPLAN:
                    sent += self._send_putzplan(
                        account.id, recipients, effective, today
                    )
                else:
                    sent += self._send_review(account.id, recipients, effective, today)
            except Exception:
                logger.exception(
                    "Wochen-Bericht %s für %s fehlgeschlagen", job, account.id
                )
        return sent

    def _send_putzplan(
        self, account_id: str, recipients: list[str], effective: Settings, today: date
    ) -> int:
        start, end = _week_bounds(today)
        # Stornierte bleiben in der Excel sichtbar (durchgestrichen);
        # als "geplant" zählen nur aktive Aufträge.
        tasks = self._task_repo.list_tasks(
            account_id=account_id, date_from=start, date_to=end
        )
        active = [t for t in tasks if t.status.value != "cancelled"]
        partners = {
            p.partner_id: p
            for p in self._partner_repo.list_partners(account_id=account_id)
        }
        week = start.isocalendar()[1]
        n_storno = len(tasks) - len(active)
        storno = f"\n❌ {n_storno} storniert" if n_storno else ""
        text = (
            f"\U0001f9f9 *Putzplan KW {week}*\n"
            f"\U0001f4c6 {format_date(start)} – {format_date(end)}\n\n"
            f"\u2705 *{len(active)} Reinigungen* geplant{storno}"
        )
        document = None
        if tasks:
            document = BotDocument(
                filename=f"Putzplan_KW{week}.xlsx",
                content=build_cleaning_xlsx(tasks, partners),
            )
        messenger = self._messenger_factory(effective)
        count = 0
        for phone in recipients:
            wa_id = normalize_wa_id(phone)
            ok = messenger.send_text(wa_id, text)
            if ok and document is not None:
                messenger.send_document(wa_id, document)
            if not ok:
                ok = self._template_fallback(
                    effective,
                    phone,
                    effective.whatsapp_template_weekly_putzplan,
                    [str(week), str(len(active))],
                )
            count += 1 if ok else 0
        return count

    def _send_review(
        self, account_id: str, recipients: list[str], effective: Settings, today: date
    ) -> int:
        start, end = _week_bounds(today)
        bookings = self._extraction_repo.list_bookings_overlapping(
            account_id=account_id, date_from=start, date_to=end
        )
        done = len(
            [
                t
                for t in self._task_repo.list_tasks(
                    account_id=account_id, date_from=start, date_to=end
                )
                if t.status.value == "done"
            ]
        )
        text = build_weekly_review(bookings, start=start, end=end, cleanings_done=done)
        messenger = self._messenger_factory(effective)
        count = 0
        for phone in recipients:
            ok = messenger.send_text(normalize_wa_id(phone), text)
            if not ok:
                week = start.isocalendar()[1]
                ok = self._template_fallback(
                    effective,
                    phone,
                    effective.whatsapp_template_weekly_review,
                    [str(week)],
                )
            count += 1 if ok else 0
        return count

    def _template_fallback(
        self,
        effective: Settings,
        phone: str,
        template_name: str,
        params: list[str],
    ) -> bool:
        """Anklopfer-Template, wenn das 24h-Fenster geschlossen ist."""
        name = template_name.strip()
        if not name:
            return False
        message = WhatsAppTemplateMessage(
            recipient_e164=phone,
            template_name=name,
            template_language=effective.whatsapp_template_language,
            template_params=params,
        )
        return self._template_sender(effective, message)


def _default_messenger(effective: Settings) -> BotMessenger:
    return MetaBotMessenger(
        access_token=effective.whatsapp_access_token,
        phone_number_id=effective.whatsapp_phone_number_id,
        api_version=effective.whatsapp_api_version,
    )


def _default_template_sender(
    effective: Settings, message: WhatsAppTemplateMessage
) -> bool:
    result = MetaCloudWhatsAppClient(effective).send_template(message)
    return bool(result.success)


def build_weekly_report_service(ctx: Any, settings: Settings) -> WeeklyReportService:
    """Baut den Service aus dem AppContext."""
    from backend.infrastructure.repositories.whatsapp_report_marker_repository import (
        WhatsAppReportMarkerRepository,
    )

    return WeeklyReportService(
        account_repo=ctx.account_repo,
        platform_settings_repo=ctx.platform_settings_repo,
        user_repo=ctx.user_repo,
        extraction_repo=ctx.extraction_repo,
        cleaning_task_repo=ctx.cleaning_task_repo,
        cleaning_partner_repo=ctx.cleaning_partner_repo,
        marker_repo=WhatsAppReportMarkerRepository(ctx.db),
        settings=settings,
    )
