"""Excel-Export (.xlsx) für den Putzplan."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from backend.features.cleaning.models import (
    CleaningPartner,
    CleaningTask,
    CleaningTaskStatus,
)

_STATUS_LABELS: dict[CleaningTaskStatus, str] = {
    CleaningTaskStatus.UNASSIGNED: "Offen (kein Partner)",
    CleaningTaskStatus.SCHEDULED: "Geplant",
    CleaningTaskStatus.NOTIFIED: "Benachrichtigt",
    CleaningTaskStatus.DONE: "Erledigt",
    CleaningTaskStatus.CANCELLED: "Storniert",
}

_HEADERS = [
    "Wohnung",
    "Zimmer",
    "Putztermin",
    "Gast",
    "Check-in",
    "Check-out",
    "Putzpartner",
    "Ansprechpartner",
    "Telefon",
    "Status",
    "Bemerkung",
    "Quelle",
    "Zuletzt aktualisiert",
]


def status_label(status: CleaningTaskStatus) -> str:
    """Deutsches Label für einen Auftragsstatus."""
    return _STATUS_LABELS.get(status, status.value)


def _fmt_date(value: date | None) -> str:
    return value.strftime("%d.%m.%Y") if value else ""


def _fmt_dt(value: datetime | None) -> str:
    return value.strftime("%d.%m.%Y %H:%M") if value else ""


def build_cleaning_xlsx(
    tasks: list[CleaningTask],
    partners_by_id: dict[str, CleaningPartner],
) -> bytes:
    """Erzeugt eine Putzplan-Arbeitsmappe als Bytes."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Putzplan"
    ws.append(_HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for task in tasks:
        partner = partners_by_id.get(task.partner_id or "")
        ws.append(
            [
                task.property_name or "",
                task.room_number or "",
                _fmt_date(task.cleaning_date),
                task.guest_name or "",
                _fmt_date(task.check_in),
                _fmt_date(task.check_out),
                partner.name if partner else "",
                partner.contact_person if partner else "",
                partner.phone if partner else "",
                status_label(task.status),
                task.note or "",
                task.source_intent or "",
                _fmt_dt(task.updated_at),
            ]
        )

    _autosize(ws, len(_HEADERS))
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def build_cleaning_ics(
    tasks: list[CleaningTask],
    partners_by_id: dict[str, CleaningPartner],
    *,
    now: datetime,
) -> bytes:
    """Erzeugt einen iCal-Kalender (.ics) mit je einem Ganztags-Termin pro Auftrag."""
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Booking-Email//Putzplan//DE",
        "CALSCALE:GREGORIAN",
    ]
    for task in tasks:
        if task.status == CleaningTaskStatus.CANCELLED or task.cleaning_date is None:
            continue
        day = task.cleaning_date.strftime("%Y%m%d")
        next_day = (task.cleaning_date + timedelta(days=1)).strftime("%Y%m%d")
        partner = partners_by_id.get(task.partner_id or "")
        summary = f"Putzen: {task.property_name or '—'}"
        desc = f"Gast: {task.guest_name or '—'} | Status: {status_label(task.status)}"
        if partner:
            desc += f" | Partner: {partner.name}"
        if task.note:
            desc += f" | Bemerkung: {task.note}"
        lines += [
            "BEGIN:VEVENT",
            f"UID:cleaning-{task.task_id}@booking-email",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{day}",
            f"DTEND;VALUE=DATE:{next_day}",
            f"SUMMARY:{_ics_escape(summary)}",
            f"DESCRIPTION:{_ics_escape(desc)}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


def _autosize(ws: object, columns: int) -> None:
    """Setzt grobe Spaltenbreiten anhand des Inhalts."""
    for col_idx in range(1, columns + 1):
        letter = get_column_letter(col_idx)
        longest = 0
        for cell in ws[letter]:  # type: ignore[index]
            value = cell.value
            if value is not None:
                longest = max(longest, len(str(value)))
        ws.column_dimensions[letter].width = min(max(longest + 2, 12), 40)  # type: ignore[attr-defined]
