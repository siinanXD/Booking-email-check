"""Putzplan-API-Logik (CRUD, Filter, Export) auf dem AppContext."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from backend.api.schemas.cleaning import (
    PartnerCreateRequest,
    PartnerItem,
    PartnersResponse,
    PartnerUpdateRequest,
    StatusEventItem,
    TaskItem,
    TasksResponse,
    TaskUpdateRequest,
)
from backend.features.cleaning.export import (
    build_cleaning_ics,
    build_cleaning_xlsx,
    status_label,
)
from backend.features.cleaning.models import (
    SOURCE_MANUAL,
    CleaningPartner,
    CleaningTask,
    CleaningTaskStatus,
)
from backend.features.cleaning.overlap import overlapping_task_ids
from backend.infrastructure.repositories.platform_settings_repository import (
    FEATURE_CLEANING_SCHEDULE,
)

if TYPE_CHECKING:
    from backend.core.config.app_context import AppContext
    from backend.infrastructure.repositories.cleaning_partner_repository import (
        CleaningPartnerRepository,
    )
    from backend.infrastructure.repositories.cleaning_task_repository import (
        CleaningTaskRepository,
    )


def feature_enabled(ctx: AppContext, account_id: str) -> bool:
    """True, wenn der Putzplan für den Account freigeschaltet ist."""
    settings = ctx.platform_settings_repo.get(account_id)
    return settings is not None and settings.feature_enabled(FEATURE_CLEANING_SCHEDULE)


def _partners(ctx: AppContext) -> CleaningPartnerRepository:
    repo = ctx.cleaning_partner_repo
    assert repo is not None
    return repo


def _tasks(ctx: AppContext) -> CleaningTaskRepository:
    repo = ctx.cleaning_task_repo
    assert repo is not None
    return repo


def _iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _partner_item(partner: CleaningPartner) -> PartnerItem:
    return PartnerItem(
        partner_id=partner.partner_id,
        name=partner.name,
        address=partner.address,
        contact_person=partner.contact_person,
        phone=partner.phone,
        locale=partner.locale,
        property_names=list(partner.property_names),
        active=partner.active,
        test_mode=partner.test_mode,
    )


def _task_item(
    task: CleaningTask, partner_name: str | None, *, overlap: bool = False
) -> TaskItem:
    return TaskItem(
        task_id=task.task_id,
        property_name=task.property_name,
        room_number=task.room_number,
        guest_name=task.guest_name,
        booking_number=task.booking_number,
        check_in=_iso(task.check_in),
        check_out=_iso(task.check_out),
        cleaning_date=_iso(task.cleaning_date),
        partner_id=task.partner_id,
        partner_name=partner_name,
        status=task.status.value,
        status_label=status_label(task.status),
        note=task.note,
        overlap=overlap,
        source_intent=task.source_intent,
        last_notification_status=task.last_notification_status,
        last_notification_error=task.last_notification_error,
        updated_at=_iso(task.updated_at),
        status_history=[
            StatusEventItem(
                status=ev.status.value,
                at=_iso(ev.at),
                source=ev.source,
                note=ev.note,
            )
            for ev in task.status_history
        ],
    )


def list_partners(ctx: AppContext, account_id: str) -> PartnersResponse:
    """Alle Putzpartner eines Accounts."""
    partners = _partners(ctx).list_partners(account_id=account_id)
    return PartnersResponse(items=[_partner_item(p) for p in partners])


def create_partner(
    ctx: AppContext, account_id: str, body: PartnerCreateRequest
) -> PartnerItem:
    """Legt einen neuen Putzpartner an."""
    partner = CleaningPartner(
        partner_id=uuid4().hex,
        account_id=account_id,
        name=body.name.strip(),
        address=body.address,
        contact_person=body.contact_person,
        phone=body.phone,
        locale=body.locale or "de",
        property_names=[p.strip() for p in body.property_names if p.strip()],
        test_mode=body.test_mode,
    )
    _partners(ctx).upsert(partner, account_id=account_id)
    return _partner_item(partner)


def update_partner(
    ctx: AppContext, account_id: str, partner_id: str, body: PartnerUpdateRequest
) -> PartnerItem | None:
    """Aktualisiert einen Putzpartner (nur gesetzte Felder)."""
    partner = _partners(ctx).get(partner_id, account_id=account_id)
    if partner is None:
        return None
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        partner.name = data["name"].strip()
    for field in ("address", "contact_person", "phone", "active", "test_mode"):
        if field in data:
            setattr(partner, field, data[field])
    if "locale" in data and data["locale"]:
        partner.locale = data["locale"]
    if "property_names" in data and data["property_names"] is not None:
        partner.property_names = [
            p.strip() for p in data["property_names"] if p.strip()
        ]
    _partners(ctx).upsert(partner, account_id=account_id)
    return _partner_item(partner)


def deactivate_partner(ctx: AppContext, account_id: str, partner_id: str) -> bool:
    """Soft-Delete eines Putzpartners."""
    return _partners(ctx).deactivate(partner_id, account_id=account_id)


def _load_tasks(
    ctx: AppContext,
    account_id: str,
    *,
    status: str | None,
    property_name: str | None,
    date_from: date | None,
    date_to: date | None,
) -> tuple[list[CleaningTask], dict[str, CleaningPartner]]:
    tasks = _tasks(ctx).list_tasks(
        account_id=account_id,
        status=status,
        property_name=property_name,
        date_from=date_from,
        date_to=date_to,
    )
    partners = {
        p.partner_id: p for p in _partners(ctx).list_partners(account_id=account_id)
    }
    return tasks, partners


def list_tasks(
    ctx: AppContext,
    account_id: str,
    *,
    status: str | None = None,
    property_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> TasksResponse:
    """Putzaufträge gefiltert auflisten."""
    tasks, partners = _load_tasks(
        ctx,
        account_id,
        status=status,
        property_name=property_name,
        date_from=date_from,
        date_to=date_to,
    )
    overlaps = overlapping_task_ids(tasks)
    items = [
        _task_item(
            t,
            partners[t.partner_id].name if t.partner_id in partners else None,
            overlap=t.task_id in overlaps,
        )
        for t in tasks
    ]
    return TasksResponse(items=items, total=len(items))


def update_task(
    ctx: AppContext, account_id: str, task_id: str, body: TaskUpdateRequest
) -> TaskItem | None:
    """Status setzen oder Partner zuweisen (markiert manuell bearbeitet)."""
    task = _tasks(ctx).get(task_id, account_id=account_id)
    if task is None:
        return None
    if body.partner_id is not None:
        task.partner_id = body.partner_id or None
        if task.partner_id and task.status == CleaningTaskStatus.UNASSIGNED:
            task.record_status(CleaningTaskStatus.SCHEDULED, source=SOURCE_MANUAL)
    if body.status is not None:
        task.record_status(CleaningTaskStatus(body.status), source=SOURCE_MANUAL)
    if "note" in body.model_dump(exclude_unset=True):
        task.note = (body.note or "").strip() or None
    task.manually_edited = True
    task.updated_at = datetime.now(UTC)
    _tasks(ctx).upsert(task, account_id=account_id)
    partner = _partners(ctx).get(task.partner_id or "", account_id=account_id)
    return _task_item(task, partner.name if partner else None)


def export_tasks_xlsx(
    ctx: AppContext,
    account_id: str,
    *,
    status: str | None = None,
    property_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> bytes:
    """Erzeugt die gefilterte Putzplan-Liste als .xlsx."""
    tasks, partners = _load_tasks(
        ctx,
        account_id,
        status=status,
        property_name=property_name,
        date_from=date_from,
        date_to=date_to,
    )
    return build_cleaning_xlsx(tasks, partners)


def export_tasks_ics(
    ctx: AppContext,
    account_id: str,
    *,
    now: datetime,
    status: str | None = None,
    property_name: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> bytes:
    """Erzeugt die gefilterte Putzplan-Liste als iCal (.ics)."""
    tasks, partners = _load_tasks(
        ctx,
        account_id,
        status=status,
        property_name=property_name,
        date_from=date_from,
        date_to=date_to,
    )
    return build_cleaning_ics(tasks, partners, now=now)
