"""API-Schemas für den Putzplan."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

from backend.features.cleaning.models import CleaningTaskStatus

_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")

# Status, die der Gastgeber manuell setzen darf.
EDITABLE_STATUSES = frozenset(
    {
        CleaningTaskStatus.SCHEDULED.value,
        CleaningTaskStatus.DONE.value,
        CleaningTaskStatus.CANCELLED.value,
    }
)


def _validate_phone(value: str | None) -> str | None:
    if value is None:
        return None
    phone = value.strip()
    if not phone:
        return None
    if not _E164_RE.match(phone):
        msg = "phone muss E.164 sein (z. B. +491701234567)"
        raise ValueError(msg)
    return phone


class PartnerCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    address: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    locale: str = "de"
    property_names: list[str] = Field(default_factory=list)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return _validate_phone(value)


class PartnerUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    address: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    locale: str | None = None
    property_names: list[str] | None = None
    active: bool | None = None

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return _validate_phone(value)


class PartnerItem(BaseModel):
    partner_id: str
    name: str
    address: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    locale: str = "de"
    property_names: list[str] = Field(default_factory=list)
    active: bool = True


class PartnersResponse(BaseModel):
    items: list[PartnerItem] = Field(default_factory=list)


class TaskItem(BaseModel):
    task_id: str
    property_name: str | None = None
    room_number: str | None = None
    guest_name: str | None = None
    booking_number: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    cleaning_date: str | None = None
    partner_id: str | None = None
    partner_name: str | None = None
    status: str
    status_label: str
    source_intent: str | None = None
    last_notification_status: str | None = None
    last_notification_error: str | None = None
    updated_at: str | None = None


class TasksResponse(BaseModel):
    items: list[TaskItem] = Field(default_factory=list)
    total: int = 0


class TaskUpdateRequest(BaseModel):
    status: str | None = None
    partner_id: str | None = None

    @field_validator("status")
    @classmethod
    def _status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in EDITABLE_STATUSES:
            allowed = ", ".join(sorted(EDITABLE_STATUSES))
            msg = f"status muss einer von {{{allowed}}} sein"
            raise ValueError(msg)
        return value
