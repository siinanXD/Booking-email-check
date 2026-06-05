"""CRUD für Unterkünfte."""

from __future__ import annotations

from backend.api.schemas.properties import (
    PropertyCreateRequest,
    PropertyListItem,
    PropertyListResponse,
    PropertyProfileResponse,
    PropertyUpdateRequest,
    PropertyYearStats,
)
from backend.core.config.factory import AppContext
from backend.core.models.entities import Property
from backend.features.booking.entity_sync import _property_id
from backend.infrastructure.repositories.property_recipient_repository import (
    PropertyWhatsAppEmployee,
)
from backend.infrastructure.repositories.property_repository import PropertyRepository


def _prop_repo(ctx: AppContext) -> PropertyRepository:
    return PropertyRepository(ctx.db)


def _to_profile(
    ctx: AppContext,
    account_id: str,
    prop: Property,
) -> PropertyProfileResponse:
    employees = ctx.property_recipient_repo.get_employees(
        prop.name,
        account_id=account_id,
    )
    return PropertyProfileResponse(
        property_id=prop.property_id,
        name=prop.name,
        platform=prop.platform,
        location=prop.location,
        contact_name=prop.contact_name,
        contact_phone=prop.contact_phone,
        contact_email=prop.contact_email,
        notes=prop.notes,
        whatsapp_phones=[employee.phone_e164 for employee in employees],
        whatsapp_employees=employees,
    )


def list_properties(
    ctx: AppContext,
    account_id: str,
    *,
    year: int | None = None,
) -> PropertyListResponse:
    from backend.api.services.property_stats_queries import (
        aggregate_property_year_stats,
    )

    props = _prop_repo(ctx).list_all(account_id=account_id)
    items: list[PropertyListItem] = []
    for prop in sorted(props, key=lambda p: p.name.lower()):
        stats: PropertyYearStats | None = None
        if year is not None:
            stats = aggregate_property_year_stats(
                ctx,
                account_id,
                prop.name,
                year=year,
            )
        items.append(
            PropertyListItem(
                property_id=prop.property_id,
                name=prop.name,
                platform=prop.platform,
                location=prop.location,
                stats=stats,
            )
        )
    return PropertyListResponse(items=items)


def get_property_profile(
    ctx: AppContext,
    account_id: str,
    property_id: str,
) -> PropertyProfileResponse | None:
    prop = _prop_repo(ctx).get_by_id(property_id, account_id=account_id)
    if prop is None:
        return None
    return _to_profile(ctx, account_id, prop)


def create_property(
    ctx: AppContext,
    account_id: str,
    body: PropertyCreateRequest,
) -> PropertyProfileResponse | None:
    name = body.name.strip()
    if not name:
        return None
    repo = _prop_repo(ctx)
    existing = {p.name.strip().lower() for p in repo.list_all(account_id=account_id)}
    if name.lower() in existing:
        return None
    prop = Property(
        property_id=_property_id(account_id, name),
        name=name,
        account_id=account_id,
    )
    repo.upsert(prop, account_id=account_id)
    ctx.property_recipient_repo.upsert(account_id, name, [])
    return _to_profile(ctx, account_id, prop)


def update_property_profile(
    ctx: AppContext,
    account_id: str,
    property_id: str,
    body: PropertyUpdateRequest,
) -> PropertyProfileResponse | None:
    repo = _prop_repo(ctx)
    prop = repo.get_by_id(property_id, account_id=account_id)
    if prop is None:
        return None
    old_name = prop.name
    updates = body.model_dump(
        exclude_unset=True,
        exclude={"whatsapp_phones", "whatsapp_employees"},
    )
    if "name" in updates and updates["name"] is not None:
        new_name = str(updates["name"]).strip()
        if not new_name:
            return None
        if new_name.lower() != old_name.lower():
            taken = {
                p.name.strip().lower()
                for p in repo.list_all(account_id=account_id)
                if p.property_id != property_id
            }
            if new_name.lower() in taken:
                return None
        updates["name"] = new_name
    prop = prop.model_copy(update=updates)
    repo.upsert(prop, account_id=account_id)
    if body.whatsapp_employees is not None:
        ctx.property_recipient_repo.upsert(
            account_id,
            prop.name,
            list(body.whatsapp_employees),
        )
    elif body.whatsapp_phones is not None:
        employees = [
            PropertyWhatsAppEmployee(phone_e164=phone) for phone in body.whatsapp_phones
        ]
        ctx.property_recipient_repo.upsert(account_id, prop.name, employees)
    elif "name" in updates and updates["name"] != old_name:
        old_employees = ctx.property_recipient_repo.get_employees(
            old_name, account_id=account_id
        )
        ctx.property_recipient_repo.upsert(account_id, prop.name, old_employees)
    return _to_profile(ctx, account_id, prop)
