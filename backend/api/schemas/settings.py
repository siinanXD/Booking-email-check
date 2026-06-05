"""Settings-API-DTOs."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from backend.infrastructure.repositories.property_recipient_repository import (
    PropertyWhatsAppEmployee,
    PropertyWhatsAppRecipients,
)


class PropertyRecipientItem(BaseModel):
    """WhatsApp-Empfänger für eine Unterkunft."""

    property_name: str = Field(min_length=1)
    employees: list[PropertyWhatsAppEmployee] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_phones(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        if data.get("employees"):
            return data
        phones = data.get("phones") or []
        if not phones:
            return data
        payload = dict(data)
        payload["employees"] = [
            {"phone_e164": phone, "locale": "de"}
            for phone in phones
            if isinstance(phone, str) and phone.strip()
        ]
        return payload

    @property
    def normalized_employees(self) -> list[PropertyWhatsAppEmployee]:
        if self.employees:
            return list(self.employees)
        return PropertyWhatsAppRecipients.model_validate(
            {
                "property_name": self.property_name,
                "phones": self.phones,
            }
        ).employees


class UserProfileSettings(BaseModel):
    """Benutzerbezogene Benachrichtigungs-Einstellungen."""

    whatsapp_phone_e164: str | None = None
    whatsapp_enabled: bool = False


class PlatformSettingsResponse(BaseModel):
    """GET-Antwort – Access Token wird maskiert."""

    whatsapp_enabled: bool = False
    whatsapp_access_token_set: bool = False
    whatsapp_phone_number_id: str = ""
    whatsapp_api_version: str = "v21.0"
    whatsapp_template_language: str = "de"
    whatsapp_template_cleaning_task: str = "booking_cleaning_task_de"
    whatsapp_template_status_notice: str = "booking_status_notice_de"
    whatsapp_template_guest_inquiry: str = "booking_guest_inquiry_de"
    whatsapp_default_recipients: str = ""
    whatsapp_test_recipient: str = ""
    outlook_mailbox: str = ""
    property_recipients: list[PropertyRecipientItem] = Field(default_factory=list)
    user_profile: UserProfileSettings = Field(default_factory=UserProfileSettings)


class PlatformSettingsUpdate(BaseModel):
    """PUT-Body – leerer Access Token = unverändert lassen."""

    whatsapp_enabled: bool | None = None
    whatsapp_access_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_api_version: str | None = None
    whatsapp_template_language: str | None = None
    whatsapp_template_cleaning_task: str | None = None
    whatsapp_template_status_notice: str | None = None
    whatsapp_template_guest_inquiry: str | None = None
    whatsapp_default_recipients: str | None = None
    whatsapp_test_recipient: str | None = None
    outlook_mailbox: str | None = None
    property_recipients: list[PropertyRecipientItem] | None = None
    user_profile: UserProfileSettings | None = None


class WhatsAppTestRequest(BaseModel):
    """Optional: andere Nummer als gespeicherte Test-Empfänger."""

    recipient_e164: str | None = None


class WhatsAppTestResponse(BaseModel):
    """Ergebnis des hello_world-Verbindungstests."""

    success: bool
    provider_message_id: str | None = None
    error: str | None = None


class WipeDataResponse(BaseModel):
    """Ergebnis von „Alle Daten löschen“."""

    deleted: dict[str, int]
