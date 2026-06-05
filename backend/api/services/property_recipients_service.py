"""WhatsApp-Empfänger pro Unterkunft."""

from __future__ import annotations

from backend.api.schemas.properties import PropertyRecipientsResponse
from backend.core.config.factory import AppContext
from backend.infrastructure.repositories.property_recipient_repository import (
    PropertyWhatsAppEmployee,
    PropertyWhatsAppRecipients,
)


def get_recipients(
    ctx: AppContext,
    account_id: str,
) -> PropertyRecipientsResponse:
    rows = ctx.property_recipient_repo.list_all(account_id)
    return PropertyRecipientsResponse(items=list(rows))


def save_recipients(
    ctx: AppContext,
    account_id: str,
    items: list[PropertyWhatsAppRecipients],
) -> PropertyRecipientsResponse:
    tuples: list[tuple[str, list[PropertyWhatsAppEmployee]]] = [
        (i.property_name, list(i.employees)) for i in items
    ]
    ctx.property_recipient_repo.replace_all(account_id, tuples)
    return get_recipients(ctx, account_id)
