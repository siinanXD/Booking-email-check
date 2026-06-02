"""Tests für effektive Settings und Settings-Repository."""

from __future__ import annotations

from config.settings import Settings
from repositories.platform_settings_repository import (
    PlatformSettingsRecord,
    PlatformSettingsRepository,
)
from services.effective_settings import (
    display_platform_settings,
    merge_platform_settings,
)


def _env(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "OPENAI_API_KEY": "test",
        "MONGODB_URI": "mongodb://localhost:27017",
        "LANGFUSE_PUBLIC_KEY": "pk",
        "LANGFUSE_SECRET_KEY": "sk",
        "WHATSAPP_ENABLED": False,
        "WHATSAPP_ACCESS_TOKEN": "env-token",
        "WHATSAPP_PHONE_NUMBER_ID": "111",
    }
    base.update(overrides)
    return Settings.model_validate(base)


def test_merge_uses_env_when_no_platform_doc() -> None:
    env = _env()
    assert merge_platform_settings(env, None) is env


def test_merge_overrides_from_platform(mock_db) -> None:
    env = _env(WHATSAPP_ENABLED=False)
    repo = PlatformSettingsRepository(mock_db)
    repo.save(
        PlatformSettingsRecord(
            whatsapp_enabled=True,
            whatsapp_access_token="db-token",
            whatsapp_phone_number_id="999",
        )
    )
    effective = merge_platform_settings(env, repo.get())
    assert effective.whatsapp_enabled is True
    assert effective.whatsapp_access_token == "db-token"
    assert effective.whatsapp_phone_number_id == "999"


def test_display_fills_empty_db_fields_from_env() -> None:
    env = _env(
        WHATSAPP_ENABLED=True,
        WHATSAPP_PHONE_NUMBER_ID="555",
        WHATSAPP_TEST_RECIPIENT="+491701111111",
        OUTLOOK_MAILBOX="mail@test.de",
    )
    stored = PlatformSettingsRecord(whatsapp_enabled=False)
    display = display_platform_settings(env, stored)
    assert display.whatsapp_phone_number_id == "555"
    assert display.whatsapp_test_recipient == "+491701111111"
    assert display.outlook_mailbox == "mail@test.de"
    assert display.whatsapp_enabled is False
