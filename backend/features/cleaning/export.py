"""Excel-Export (.xlsx) für den Putzplan."""

from __future__ import annotations

from datetime import date, datetime
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
    "Putztermin",
    "Gast",
    "Check-in",
    "Check-out",
    "Putzpartner",
    "Ansprechpartner",
    "Telefon",
    "Status",
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
        room = f" – Zimmer {task.room_number}" if task.room_number else ""
        ws.append(
            [
                f"{task.property_name or ''}{room}",
                _fmt_date(task.cleaning_date),
                task.guest_name or "",
                _fmt_date(task.check_in),
                _fmt_date(task.check_out),
                partner.name if partner else "",
                partner.contact_person if partner else "",
                partner.phone if partner else "",
                status_label(task.status),
                task.source_intent or "",
                _fmt_dt(task.updated_at),
            ]
        )

    _autosize(ws, len(_HEADERS))
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


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
