"""WhatsApp-bezogene Einstellungen (Mixin für Settings)."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class WhatsAppSettingsMixin(BaseSettings):
    """Alle WHATSAPP_*-Umgebungsvariablen; siehe `.env.example`."""

    whatsapp_webhook_verify_token: str = Field(
        default="", alias="WHATSAPP_WEBHOOK_VERIFY_TOKEN"
    )
    whatsapp_app_secret: str = Field(default="", alias="WHATSAPP_APP_SECRET")
    whatsapp_echo_mode: bool = Field(default=False, alias="WHATSAPP_ECHO_MODE")
    whatsapp_bot_enabled: bool = Field(default=False, alias="WHATSAPP_BOT_ENABLED")
    whatsapp_bot_intent_model: str = Field(
        default="gpt-4o-mini",
        alias="WHATSAPP_BOT_INTENT_MODEL",
    )
    whatsapp_weekly_putzplan_enabled: bool = Field(
        default=False, alias="WHATSAPP_WEEKLY_PUTZPLAN_ENABLED"
    )
    whatsapp_weekly_putzplan_weekday: int = Field(
        default=0, ge=0, le=6, alias="WHATSAPP_WEEKLY_PUTZPLAN_WEEKDAY"
    )
    whatsapp_weekly_putzplan_hour: int = Field(
        default=7, ge=0, le=23, alias="WHATSAPP_WEEKLY_PUTZPLAN_HOUR"
    )
    whatsapp_template_weekly_putzplan: str = Field(
        default="", alias="WHATSAPP_TEMPLATE_WEEKLY_PUTZPLAN"
    )
    whatsapp_weekly_review_enabled: bool = Field(
        default=False, alias="WHATSAPP_WEEKLY_REVIEW_ENABLED"
    )
    whatsapp_weekly_review_weekday: int = Field(
        default=4, ge=0, le=6, alias="WHATSAPP_WEEKLY_REVIEW_WEEKDAY"
    )
    whatsapp_weekly_review_hour: int = Field(
        default=16, ge=0, le=23, alias="WHATSAPP_WEEKLY_REVIEW_HOUR"
    )
    whatsapp_template_weekly_review: str = Field(
        default="", alias="WHATSAPP_TEMPLATE_WEEKLY_REVIEW"
    )
    whatsapp_enabled: bool = Field(default=False, alias="WHATSAPP_ENABLED")
    whatsapp_access_token: str = Field(default="", alias="WHATSAPP_ACCESS_TOKEN")
    whatsapp_phone_number_id: str = Field(default="", alias="WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_api_version: str = Field(default="v21.0", alias="WHATSAPP_API_VERSION")
    whatsapp_template_language: str = Field(
        default="de",
        alias="WHATSAPP_TEMPLATE_LANGUAGE",
    )
    whatsapp_template_cleaning_task: str = Field(
        default="booking_cleaning_task_de",
        alias="WHATSAPP_TEMPLATE_CLEANING_TASK",
    )
    whatsapp_template_status_notice: str = Field(
        default="booking_status_notice_de",
        alias="WHATSAPP_TEMPLATE_STATUS_NOTICE",
    )
    whatsapp_template_guest_inquiry: str = Field(
        default="booking_guest_inquiry_de",
        alias="WHATSAPP_TEMPLATE_GUEST_INQUIRY",
    )
    whatsapp_template_cleaning_cancelled: str = Field(
        default="booking_cleaning_cancelled_de",
        alias="WHATSAPP_TEMPLATE_CLEANING_CANCELLED",
    )
    whatsapp_template_cleaning_reminder: str = Field(
        default="booking_cleaning_reminder_de",
        alias="WHATSAPP_TEMPLATE_CLEANING_REMINDER",
    )
    whatsapp_default_recipients: str = Field(
        default="",
        alias="WHATSAPP_DEFAULT_RECIPIENTS",
    )
    whatsapp_test_recipient: str = Field(
        default="",
        alias="WHATSAPP_TEST_RECIPIENT",
    )
    whatsapp_auto_on_detect: bool = Field(
        default=False,
        alias="WHATSAPP_AUTO_ON_DETECT",
    )
    whatsapp_template_support_ticket: str = Field(
        default="platform_support_ticket_de",
        alias="WHATSAPP_TEMPLATE_SUPPORT_TICKET",
    )
    platform_admin_whatsapp_e164: str = Field(
        default="",
        alias="PLATFORM_ADMIN_WHATSAPP_E164",
    )
