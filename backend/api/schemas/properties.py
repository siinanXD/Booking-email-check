"""Properties-API-Schemas."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

from backend.infrastructure.repositories.property_recipient_repository import (
    PropertyWhatsAppRecipients,
)

_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")


class PropertyRecipientsResponse(BaseModel):
    items: list[PropertyWhatsAppRecipients] = Field(default_factory=list)


class PropertyRecipientsUpdateRequest(BaseModel):
    items: list[PropertyWhatsAppRecipients] = Field(default_factory=list)


class PropertyHistoryItem(BaseModel):
    correlation_id: str
    subject: str = ""
    received_at: str | None = None
    intent: str | None = None
    booking_number: str | None = None
    property_name: str | None = None


class PropertyHistoryResponse(BaseModel):
    items: list[PropertyHistoryItem] = Field(default_factory=list)
    total: int = 0


class PropertySuggestion(BaseModel):
    property_name: str
    mail_count: int = 0


class PropertySuggestionsResponse(BaseModel):
    items: list[PropertySuggestion] = Field(default_factory=list)


class PropertyCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    from_suggestion: bool = False


class PropertyYearStats(BaseModel):
    year: int
    booked_days: int = 0
    revenue: float = 0.0
    booking_count: int = 0
    incomplete_data_count: int = 0


class PropertyProfileResponse(BaseModel):
    property_id: str
    name: str
    platform: str | None = None
    location: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    notes: str | None = None
    whatsapp_phones: list[str] = Field(default_factory=list)


class PropertyListItem(BaseModel):
    property_id: str
    name: str
    platform: str | None = None
    location: str | None = None
    stats: PropertyYearStats | None = None


class PropertyListResponse(BaseModel):
    items: list[PropertyListItem] = Field(default_factory=list)


class PropertyUpdateRequest(BaseModel):
    name: str | None = None
    platform: str | None = None
    location: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    notes: str | None = None
    whatsapp_phones: list[str] | None = None

    @field_validator("contact_phone")
    @classmethod
    def validate_contact_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        phone = value.strip()
        if not phone:
            return None
        if not _E164_RE.match(phone):
            msg = "contact_phone muss E.164 sein (z. B. +491701234567)"
            raise ValueError(msg)
        return phone

    @field_validator("whatsapp_phones")
    @classmethod
    def validate_whatsapp_phones(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        phones: list[str] = []
        for raw in value:
            phone = raw.strip()
            if not phone:
                continue
            if not _E164_RE.match(phone):
                msg = "whatsapp_phones müssen E.164 sein (z. B. +491701234567)"
                raise ValueError(msg)
            phones.append(phone)
        return phones
