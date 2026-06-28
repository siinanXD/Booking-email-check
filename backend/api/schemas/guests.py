"""DTOs für DSGVO-Gastfunktionen (Auskunft Art. 15, Löschung Art. 17)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GuestConsent(BaseModel):
    """Dokumentierte WhatsApp-Einwilligung eines Gastes/Empfängers."""

    whatsapp_consent: bool = False
    consent_at: str | None = None


class GuestMailItem(BaseModel):
    """Eine Mail im Auskunfts-Export."""

    correlation_id: str
    subject: str = ""
    received_at: str | None = None
    intent: str | None = None


class GuestExportResponse(BaseModel):
    """Auskunft nach Art. 15 DSGVO."""

    guest_id: str
    email: str
    consent: GuestConsent = Field(default_factory=GuestConsent)
    mails: list[GuestMailItem] = Field(default_factory=list)
    mail_count: int = 0
    generated_at: str


class GuestDeleteResponse(BaseModel):
    """Ergebnis der Löschung nach Art. 17 DSGVO."""

    guest_id: str
    deleted: dict[str, int]


class GuestConsentUpdate(BaseModel):
    """Setzt die WhatsApp-Einwilligung."""

    whatsapp_consent: bool
