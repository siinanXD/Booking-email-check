"""WhatsApp-Vorschau ohne Versand."""

from __future__ import annotations

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.api.schemas.review_whatsapp import (
    WhatsAppPreviewMessage,
    WhatsAppPreviewResponse,
)
from backend.core.config.factory import AppContext
from backend.core.config.settings import Settings
from backend.core.models.notification import NotificationKind
from backend.features.notifications.notification_template_payload import (
    build_template_payload,
    kind_for_extraction,
    parse_recipient_list,
)
from backend.features.notifications.whatsapp_locale import DEFAULT_EMPLOYEE_LOCALE
from backend.features.notifications.whatsapp_template_render import render_whatsapp_body
from backend.features.platform.effective_settings import merge_platform_settings
from backend.infrastructure.repositories.property_recipient_repository import (
    PropertyRecipientRepository,
)


def build_whatsapp_preview(
    ctx: AppContext,
    account_id: str,
    correlation_id: str,
    extraction: BookingExtraction,
) -> WhatsAppPreviewResponse:
    """Baut Template-Vorschau für alle konfigurierten Empfänger."""
    platform = ctx.platform_settings_repo.get(account_id)
    settings = merge_platform_settings(ctx.settings, platform)
    if not settings.whatsapp_enabled:
        return WhatsAppPreviewResponse(
            correlation_id=correlation_id,
            enabled=False,
            note="WhatsApp ist deaktiviert.",
        )
    kind = kind_for_extraction(extraction)
    if kind is None:
        return WhatsAppPreviewResponse(
            correlation_id=correlation_id,
            enabled=True,
            note="Kein Template für diesen Intent.",
        )
    recipients = _preview_recipients(
        ctx.property_recipient_repo,
        ctx.user_repo.list_whatsapp_recipient_phones(account_id),
        settings.whatsapp_default_recipients,
        settings.whatsapp_template_language,
        extraction,
        account_id=account_id,
    )
    if not recipients:
        return WhatsAppPreviewResponse(
            correlation_id=correlation_id,
            enabled=True,
            note="Keine Empfänger konfiguriert.",
        )
    _, params_de, _ = build_template_payload(
        kind,
        extraction,
        settings,
        locale=DEFAULT_EMPLOYEE_LOCALE,
    )
    body_de = render_whatsapp_body(kind, params_de, DEFAULT_EMPLOYEE_LOCALE)
    messages = [
        _preview_message(
            phone=phone,
            locale=locale,
            role=role,
            kind=kind,
            extraction=extraction,
            settings=settings,
            body_de=body_de,
        )
        for phone, locale, role in recipients
    ]
    return WhatsAppPreviewResponse(
        correlation_id=correlation_id,
        enabled=True,
        messages=messages,
    )


def _preview_message(
    *,
    phone: str,
    locale: str,
    role: str,
    kind: NotificationKind,
    extraction: BookingExtraction,
    settings: Settings,
    body_de: str,
) -> WhatsAppPreviewMessage:
    host_locale = settings.whatsapp_template_language.strip() or DEFAULT_EMPLOYEE_LOCALE
    effective_locale = locale
    if kind != NotificationKind.BOOKING_CLEANING_TASK or role != "employee":
        effective_locale = host_locale
    template_name, params, template_language = build_template_payload(
        kind,
        extraction,
        settings,
        locale=effective_locale,
    )
    generated_body = render_whatsapp_body(kind, params, template_language)
    return WhatsAppPreviewMessage(
        recipient_e164=phone,
        template_name=template_name,
        template_language=template_language,
        template_params=params,
        kind=kind.value,
        recipient_role=role,
        generated_body=generated_body,
        generated_body_de=body_de,
    )


def _preview_recipients(
    property_repo: PropertyRecipientRepository,
    user_phones: list[str],
    default_raw: str,
    host_locale: str,
    extraction: BookingExtraction,
    *,
    account_id: str,
) -> list[tuple[str, str, str]]:
    from backend.ai.domain.booking.taxonomy import BookingIntent

    locale = host_locale.strip() or DEFAULT_EMPLOYEE_LOCALE
    targets: dict[str, tuple[str, str]] = {}
    for phone in user_phones:
        targets[phone] = (locale, "host")
    for phone in parse_recipient_list(default_raw):
        targets[phone] = (locale, "host")
    intent = extraction.intent
    if intent in (BookingIntent.NEW_BOOKING, None):
        for employee in property_repo.get_employees(
            extraction.property_name,
            account_id=account_id,
        ):
            targets[employee.phone_e164] = (employee.locale, "employee")
    return sorted((phone, loc, role) for phone, (loc, role) in targets.items())
