"""Zusammenführung von .env-Settings und DB-Plattform-Einstellungen."""

from __future__ import annotations

from backend.core.config.settings import Settings
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRecord,
)


def merge_platform_settings(
    env: Settings,
    platform: PlatformSettingsRecord | None,
) -> Settings:
    """Erzeugt effektive Settings: DB-Werte überschreiben .env wenn gesetzt."""
    if platform is None:
        return env

    overrides: dict[str, object] = {}

    if platform.whatsapp_access_token.strip():
        overrides["WHATSAPP_ACCESS_TOKEN"] = platform.whatsapp_access_token.strip()
    if platform.whatsapp_phone_number_id.strip():
        overrides["WHATSAPP_PHONE_NUMBER_ID"] = (
            platform.whatsapp_phone_number_id.strip()
        )
    if platform.whatsapp_api_version.strip():
        overrides["WHATSAPP_API_VERSION"] = platform.whatsapp_api_version.strip()
    if platform.whatsapp_template_language.strip():
        overrides["WHATSAPP_TEMPLATE_LANGUAGE"] = (
            platform.whatsapp_template_language.strip()
        )
    if platform.whatsapp_template_cleaning_task.strip():
        overrides["WHATSAPP_TEMPLATE_CLEANING_TASK"] = (
            platform.whatsapp_template_cleaning_task.strip()
        )
    if platform.whatsapp_template_status_notice.strip():
        overrides["WHATSAPP_TEMPLATE_STATUS_NOTICE"] = (
            platform.whatsapp_template_status_notice.strip()
        )
    if platform.whatsapp_template_guest_inquiry.strip():
        overrides["WHATSAPP_TEMPLATE_GUEST_INQUIRY"] = (
            platform.whatsapp_template_guest_inquiry.strip()
        )
    if platform.whatsapp_default_recipients.strip():
        overrides["WHATSAPP_DEFAULT_RECIPIENTS"] = (
            platform.whatsapp_default_recipients.strip()
        )
    if platform.whatsapp_test_recipient.strip():
        overrides["WHATSAPP_TEST_RECIPIENT"] = platform.whatsapp_test_recipient.strip()
    if platform.outlook_mailbox.strip():
        overrides["OUTLOOK_MAILBOX"] = platform.outlook_mailbox.strip()

    overrides["WHATSAPP_ENABLED"] = platform.whatsapp_enabled

    base = env.model_dump(by_alias=True)
    base.update(overrides)
    return Settings.model_validate(base)


def platform_from_env(env: Settings, account_id: str) -> PlatformSettingsRecord:
    """Initialisiert DB-Dokument aus aktuellen .env-Werten.

    Credentials (access_token, phone_number_id) werden bewusst NICHT kopiert,
    damit merge_platform_settings immer den aktuellen Env-Wert nutzt — außer
    der Tenant hat seine eigenen Credentials explizit eingetragen.
    """
    return PlatformSettingsRecord(
        id=account_id,
        whatsapp_enabled=env.whatsapp_enabled,
        whatsapp_access_token="",
        whatsapp_phone_number_id="",
        whatsapp_api_version=env.whatsapp_api_version,
        whatsapp_template_language=env.whatsapp_template_language,
        whatsapp_template_cleaning_task=env.whatsapp_template_cleaning_task,
        whatsapp_template_status_notice=env.whatsapp_template_status_notice,
        whatsapp_template_guest_inquiry=env.whatsapp_template_guest_inquiry,
        whatsapp_default_recipients=env.whatsapp_default_recipients,
        whatsapp_test_recipient=env.whatsapp_test_recipient,
        outlook_mailbox=env.outlook_mailbox or "",
    )


def _pick_str(stored: str, env_value: str) -> str:
    cleaned = stored.strip()
    if cleaned:
        return cleaned
    return env_value.strip()


def display_platform_settings(
    env: Settings,
    stored: PlatformSettingsRecord | None,
) -> PlatformSettingsRecord:
    """Anzeige-Werte: gespeicherte DB-Felder, sonst Fallback aus .env."""
    defaults = platform_from_env(env, stored.id if stored else "unknown")
    if stored is None:
        return PlatformSettingsRecord(
            id="unknown",
            whatsapp_enabled=defaults.whatsapp_enabled,
            whatsapp_access_token=env.whatsapp_access_token,
            whatsapp_phone_number_id=env.whatsapp_phone_number_id,
            whatsapp_api_version=defaults.whatsapp_api_version,
            whatsapp_template_language=defaults.whatsapp_template_language,
            whatsapp_template_cleaning_task=defaults.whatsapp_template_cleaning_task,
            whatsapp_template_status_notice=defaults.whatsapp_template_status_notice,
            whatsapp_template_guest_inquiry=defaults.whatsapp_template_guest_inquiry,
            whatsapp_default_recipients=defaults.whatsapp_default_recipients,
            whatsapp_test_recipient=defaults.whatsapp_test_recipient,
            outlook_mailbox=defaults.outlook_mailbox,
        )
    return PlatformSettingsRecord(
        id=stored.id,
        whatsapp_enabled=stored.whatsapp_enabled,
        whatsapp_access_token=_pick_str(
            stored.whatsapp_access_token, env.whatsapp_access_token
        ),
        whatsapp_phone_number_id=_pick_str(
            stored.whatsapp_phone_number_id,
            env.whatsapp_phone_number_id,
        ),
        whatsapp_api_version=_pick_str(
            stored.whatsapp_api_version, defaults.whatsapp_api_version
        ),
        whatsapp_template_language=_pick_str(
            stored.whatsapp_template_language,
            defaults.whatsapp_template_language,
        ),
        whatsapp_template_cleaning_task=_pick_str(
            stored.whatsapp_template_cleaning_task,
            defaults.whatsapp_template_cleaning_task,
        ),
        whatsapp_template_status_notice=_pick_str(
            stored.whatsapp_template_status_notice,
            defaults.whatsapp_template_status_notice,
        ),
        whatsapp_template_guest_inquiry=_pick_str(
            stored.whatsapp_template_guest_inquiry,
            defaults.whatsapp_template_guest_inquiry,
        ),
        whatsapp_default_recipients=_pick_str(
            stored.whatsapp_default_recipients,
            defaults.whatsapp_default_recipients,
        ),
        whatsapp_test_recipient=_pick_str(
            stored.whatsapp_test_recipient,
            defaults.whatsapp_test_recipient,
        ),
        outlook_mailbox=_pick_str(stored.outlook_mailbox, defaults.outlook_mailbox),
        updated_at=stored.updated_at,
    )
