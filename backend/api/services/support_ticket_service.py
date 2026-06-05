"""Support-Ticket-Fachlogik."""

from __future__ import annotations

import time

from backend.api.schemas.support_ticket import (
    AdminSupportTicketListResponse,
    AdminSupportTicketResponse,
    PlatformAdminConfigResponse,
    PlatformAdminConfigUpdateRequest,
    SupportTicketCreateRequest,
    SupportTicketListResponse,
    SupportTicketResponse,
)
from backend.core.config.factory import AppContext
from backend.core.config.settings import Settings
from backend.core.models.support_ticket import SupportTicketStatus, SupportTicketUrgency
from backend.features.notifications.notification_template_payload import _E164_RE
from backend.features.support.support_ticket_notify_service import (
    SupportTicketNotifyService,
    effective_support_admin_settings,
)

_RATE_BUCKETS: dict[str, list[float]] = {}
_RATE_LIMIT_PER_HOUR = 10


def _check_rate_limit(user_id: str) -> bool:
    now = time.time()
    bucket = _RATE_BUCKETS.setdefault(user_id, [])
    bucket[:] = [t for t in bucket if now - t < 3600]
    if len(bucket) >= _RATE_LIMIT_PER_HOUR:
        return False
    bucket.append(now)
    return True


def _to_response(ticket: object) -> SupportTicketResponse:
    from backend.core.models.support_ticket import SupportTicketRecord

    assert isinstance(ticket, SupportTicketRecord)
    return SupportTicketResponse(
        ticket_id=ticket.ticket_id,
        account_id=ticket.account_id,
        created_by_user_id=ticket.created_by_user_id,
        created_by_email=ticket.created_by_email,
        subject=ticket.subject,
        message=ticket.message,
        urgency=ticket.urgency,
        status=ticket.status,
        admin_note=ticket.admin_note,
        whatsapp_notify_status=ticket.whatsapp_notify_status,
        created_at=ticket.created_at.isoformat(),
        updated_at=ticket.updated_at.isoformat(),
    )


def _to_admin_response(
    ticket: object,
    *,
    account_display_name: str | None = None,
) -> AdminSupportTicketResponse:
    from backend.core.models.support_ticket import SupportTicketRecord

    assert isinstance(ticket, SupportTicketRecord)
    base = _to_response(ticket)
    return AdminSupportTicketResponse(
        **base.model_dump(),
        whatsapp_notify_error=ticket.whatsapp_notify_error,
        whatsapp_message_id=ticket.whatsapp_message_id,
        account_display_name=account_display_name,
    )


class RateLimitExceededError(Exception):
    """Zu viele Tickets pro Stunde."""


class SupportTicketNotFoundError(Exception):
    """Ticket nicht gefunden."""


def create_ticket(
    ctx: AppContext,
    settings: Settings,
    *,
    account_id: str,
    user_id: str,
    user_email: str,
    body: SupportTicketCreateRequest,
    notify_service: SupportTicketNotifyService | None = None,
) -> SupportTicketResponse:
    if not _check_rate_limit(user_id):
        raise RateLimitExceededError()

    ticket = ctx.support_ticket_repo.create(
        account_id=account_id,
        created_by_user_id=user_id,
        created_by_email=user_email,
        message=body.message,
        urgency=body.urgency,
        subject=body.subject,
    )

    account = ctx.account_repo.get_by_id(account_id)
    display_name = account.display_name if account else account_id
    notifier = notify_service or SupportTicketNotifyService(
        settings,
        ctx.platform_admin_config_repo,
    )
    wa_status, wa_error, wa_msg_id = notifier.notify_new_ticket(
        ticket,
        account_display_name=display_name,
    )
    updated = ctx.support_ticket_repo.update_whatsapp_status(
        ticket.ticket_id,
        status=wa_status,  # type: ignore[arg-type]
        error=wa_error,
        message_id=wa_msg_id,
    )
    assert updated is not None
    return _to_response(updated)


def list_tenant_tickets(
    ctx: AppContext,
    account_id: str,
    *,
    limit: int = 50,
) -> SupportTicketListResponse:
    items = ctx.support_ticket_repo.list_for_account(account_id, limit=limit)
    responses = [_to_response(t) for t in items]
    return SupportTicketListResponse(items=responses, total=len(responses))


def list_admin_tickets(
    ctx: AppContext,
    *,
    status: SupportTicketStatus | None = None,
    urgency: SupportTicketUrgency | None = None,
    account_id: str | None = None,
    limit: int = 100,
) -> AdminSupportTicketListResponse:
    tickets = ctx.support_ticket_repo.list_admin(
        status=status,
        urgency=urgency,
        account_id=account_id,
        limit=limit,
    )
    accounts = {a.id: a.display_name for a in ctx.account_repo.list_by_status(None)}
    items = [
        _to_admin_response(t, account_display_name=accounts.get(t.account_id))
        for t in tickets
    ]
    return AdminSupportTicketListResponse(
        items=items,
        total=len(items),
        open_count=ctx.support_ticket_repo.count_open(),
    )


def get_admin_ticket(ctx: AppContext, ticket_id: str) -> AdminSupportTicketResponse:
    ticket = ctx.support_ticket_repo.get_by_ticket_id(ticket_id)
    if ticket is None:
        raise SupportTicketNotFoundError()
    account = ctx.account_repo.get_by_id(ticket.account_id)
    return _to_admin_response(
        ticket,
        account_display_name=account.display_name if account else None,
    )


def patch_admin_ticket(
    ctx: AppContext,
    ticket_id: str,
    *,
    status: SupportTicketStatus | None = None,
    admin_note: str | None = None,
) -> AdminSupportTicketResponse:
    if ctx.support_ticket_repo.get_by_ticket_id(ticket_id) is None:
        raise SupportTicketNotFoundError()
    updated = ctx.support_ticket_repo.update_admin(
        ticket_id,
        status=status,
        admin_note=admin_note,
    )
    assert updated is not None
    account = ctx.account_repo.get_by_id(updated.account_id)
    return _to_admin_response(
        updated,
        account_display_name=account.display_name if account else None,
    )


def retry_whatsapp(
    ctx: AppContext,
    settings: Settings,
    ticket_id: str,
    *,
    notify_service: SupportTicketNotifyService | None = None,
) -> AdminSupportTicketResponse:
    ticket = ctx.support_ticket_repo.get_by_ticket_id(ticket_id)
    if ticket is None:
        raise SupportTicketNotFoundError()
    account = ctx.account_repo.get_by_id(ticket.account_id)
    display_name = account.display_name if account else ticket.account_id
    notifier = notify_service or SupportTicketNotifyService(
        settings,
        ctx.platform_admin_config_repo,
    )
    wa_status, wa_error, wa_msg_id = notifier.notify_new_ticket(
        ticket,
        account_display_name=display_name,
    )
    updated = ctx.support_ticket_repo.update_whatsapp_status(
        ticket_id,
        status=wa_status,  # type: ignore[arg-type]
        error=wa_error,
        message_id=wa_msg_id,
    )
    assert updated is not None
    return _to_admin_response(
        updated,
        account_display_name=display_name,
    )


def get_platform_admin_config(
    ctx: AppContext,
    settings: Settings,
) -> PlatformAdminConfigResponse:
    stored = ctx.platform_admin_config_repo.get_or_default()
    phone, template = effective_support_admin_settings(
        settings, ctx.platform_admin_config_repo
    )
    return PlatformAdminConfigResponse(
        platform_admin_whatsapp_e164=phone,
        whatsapp_template_support_ticket=template,
        updated_at=stored.updated_at.isoformat() if stored.updated_at else None,
    )


def update_platform_admin_config(
    ctx: AppContext,
    body: PlatformAdminConfigUpdateRequest,
    *,
    user_id: str | None,
) -> PlatformAdminConfigResponse:
    current = ctx.platform_admin_config_repo.get_or_default()
    if body.platform_admin_whatsapp_e164 is not None:
        phone = body.platform_admin_whatsapp_e164.strip()
        if phone and not _E164_RE.match(phone):
            raise ValueError("Ungültige E.164-Nummer")
        current.platform_admin_whatsapp_e164 = phone
    if body.whatsapp_template_support_ticket is not None:
        current.whatsapp_template_support_ticket = (
            body.whatsapp_template_support_ticket.strip()
            or "platform_support_ticket_de"
        )
    ctx.platform_admin_config_repo.save(current, updated_by_user_id=user_id)
    return PlatformAdminConfigResponse(
        platform_admin_whatsapp_e164=current.platform_admin_whatsapp_e164,
        whatsapp_template_support_ticket=current.whatsapp_template_support_ticket,
        updated_at=current.updated_at.isoformat(),
    )
