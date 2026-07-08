"""Tests: geplante Wochen-Berichte (Putzplan Mo, Review Fr)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.core.config.settings import Settings
from backend.features.cleaning.models import CleaningTask, CleaningTaskStatus
from backend.features.whatsapp_bot.deps import BotDeps
from backend.features.whatsapp_bot.weekly_reports import (
    WeeklyReportService,
    build_weekly_review,
)
from backend.infrastructure.repositories.user_repository import UserRepository
from backend.infrastructure.repositories.whatsapp_report_marker_repository import (
    WhatsAppReportMarkerRepository,
)
from tests.whatsapp_bot.conftest import FakeMessenger

_WEEK_START = date(2026, 7, 6)  # Montag KW 28
_WEEK_END = date(2026, 7, 12)
# Freitag 16:00 bzw. Montag 07:00 (Europe/Berlin = UTC+2 im Juli)
_FRIDAY_16 = datetime(2026, 7, 10, 14, 0, tzinfo=UTC)
_MONDAY_7 = datetime(2026, 7, 6, 5, 0, tzinfo=UTC)


def _booking(
    check_in: date,
    check_out: date,
    *,
    price: float | None = None,
    prop: str = "FeWo Seeblick",
) -> BookingExtraction:
    return BookingExtraction(
        intent="new_booking",
        guest_name="Max",
        property_name=prop,
        check_in=check_in,
        check_out=check_out,
        price=price,
    )


def test_review_zaehlt_naechte_anreisen_und_umsatz() -> None:
    bookings = [
        # komplett in der Woche: 3 Nächte, Anreise + Abreise, 300 € Umsatz
        _booking(date(2026, 7, 7), date(2026, 7, 10), price=300.0),
        # ragt links rein: nur 2 Nächte zählen, keine Anreise, kein Umsatz,
        # aber Abreise am 08.07. liegt in der Woche
        _booking(date(2026, 7, 1), date(2026, 7, 8), price=999.0, prop="FeWo Berg"),
    ]
    text = build_weekly_review(bookings, start=_WEEK_START, end=_WEEK_END)
    assert "*5 Übernachtungen*" in text
    assert "1 Anreisen" in text
    assert "2 Abreisen" in text
    assert "300.00 €" in text
    assert "Meistgebucht: *FeWo Seeblick*" in text


def test_review_leere_woche() -> None:
    text = build_weekly_review([], start=_WEEK_START, end=_WEEK_END)
    assert "*0 Übernachtungen*" in text
    assert "Keine Buchungen" in text


def _settings(**overrides: Any) -> Settings:
    payload: dict[str, Any] = {
        "OPENAI_API_KEY": "sk-test",
        "MONGODB_URI": "mongodb://localhost",
        "LANGFUSE_PUBLIC_KEY": "pk-test",
        "LANGFUSE_SECRET_KEY": "sk-test",
        "LLM_MODE": "mock",
        "WHATSAPP_ACCESS_TOKEN": "token",
        "WHATSAPP_PHONE_NUMBER_ID": "12345",
        "WHATSAPP_WEEKLY_PUTZPLAN_ENABLED": "true",
        "WHATSAPP_WEEKLY_REVIEW_ENABLED": "true",
        **overrides,
    }
    return Settings.model_validate(payload)


def _recording_sender(calls: list[Any]) -> Any:
    def _send(eff: Any, msg: Any) -> bool:
        calls.append(msg)
        return True

    return _send


class _StubPlatformSettings:
    def get(self, account_id: str) -> None:
        return None


@pytest.fixture
def weekly_service_parts(
    mock_db: Any,
    bot_deps: BotDeps,
    user_repo: UserRepository,
    fake_messenger: FakeMessenger,
) -> tuple[WeeklyReportService, FakeMessenger, list[Any]]:
    user = user_repo.create(
        "owner@test.local", "hash", account_id="acc-1", role="owner"
    )
    user_repo.update_whatsapp_profile(
        user.id, whatsapp_phone_e164="+4915711111111", whatsapp_enabled=True
    )
    template_calls: list[Any] = []
    service = WeeklyReportService(
        account_repo=SimpleNamespace(
            list_by_status=lambda status: [SimpleNamespace(id="acc-1")]
        ),
        platform_settings_repo=_StubPlatformSettings(),
        user_repo=user_repo,
        extraction_repo=bot_deps.extraction_repo,
        cleaning_task_repo=bot_deps.cleaning_task_repo,
        cleaning_partner_repo=bot_deps.cleaning_partner_repo,
        marker_repo=WhatsAppReportMarkerRepository(mock_db),
        settings=_settings(),
        messenger_factory=lambda eff: fake_messenger,
        template_sender=_recording_sender(template_calls),
    )
    return service, fake_messenger, template_calls


def test_review_freitags_versendet_und_dedupe(
    weekly_service_parts: tuple[WeeklyReportService, FakeMessenger, list[Any]],
    bot_deps: BotDeps,
) -> None:
    service, messenger, _ = weekly_service_parts
    bot_deps.extraction_repo.save(
        "c1",
        "m1",
        _booking(date(2026, 7, 7), date(2026, 7, 10), price=300.0),
        account_id="acc-1",
    )
    assert service.run_due(_FRIDAY_16) == 1
    assert "Wochen-Review KW 28" in messenger.all_texts
    assert "300.00 €" in messenger.all_texts
    # zweiter Lauf in derselben Woche: Marker verhindert Doppelversand
    assert service.run_due(_FRIDAY_16) == 0
    assert len(messenger.texts) == 1


def test_review_nicht_faellig_am_donnerstag(
    weekly_service_parts: tuple[WeeklyReportService, FakeMessenger, list[Any]],
) -> None:
    service, messenger, _ = weekly_service_parts
    thursday = datetime(2026, 7, 9, 14, 0, tzinfo=UTC)
    assert service.run_due(thursday) == 0
    assert messenger.texts == []


def test_putzplan_montags_mit_excel(
    weekly_service_parts: tuple[WeeklyReportService, FakeMessenger, list[Any]],
    bot_deps: BotDeps,
) -> None:
    service, messenger, _ = weekly_service_parts
    bot_deps.cleaning_task_repo.upsert(
        CleaningTask(
            task_id="t1",
            account_id="acc-1",
            property_name="FeWo Seeblick",
            cleaning_date=date(2026, 7, 8),
            status=CleaningTaskStatus.SCHEDULED,
        )
    )
    assert service.run_due(_MONDAY_7) == 1
    assert "Putzplan KW 28" in messenger.all_texts
    assert len(messenger.documents) == 1
    _, document = messenger.documents[0]
    assert document.filename == "Putzplan_KW28.xlsx"
    assert document.content[:2] == b"PK"


def test_template_fallback_wenn_fenster_zu(
    mock_db: Any, bot_deps: BotDeps, user_repo: UserRepository
) -> None:
    """Session-Versand scheitert → konfiguriertes Template klopft an."""
    user = user_repo.create("o@test.local", "hash", account_id="acc-1", role="owner")
    user_repo.update_whatsapp_profile(
        user.id, whatsapp_phone_e164="+4915711111111", whatsapp_enabled=True
    )

    class _FailingMessenger(FakeMessenger):
        def send_text(self, recipient_wa_id: str, text: str) -> bool:
            return False

    template_calls: list[Any] = []
    service = WeeklyReportService(
        account_repo=SimpleNamespace(
            list_by_status=lambda status: [SimpleNamespace(id="acc-1")]
        ),
        platform_settings_repo=_StubPlatformSettings(),
        user_repo=user_repo,
        extraction_repo=bot_deps.extraction_repo,
        cleaning_task_repo=bot_deps.cleaning_task_repo,
        cleaning_partner_repo=bot_deps.cleaning_partner_repo,
        marker_repo=WhatsAppReportMarkerRepository(mock_db),
        settings=_settings(WHATSAPP_TEMPLATE_WEEKLY_REVIEW="weekly_review_de"),
        messenger_factory=lambda eff: _FailingMessenger(),
        template_sender=_recording_sender(template_calls),
    )
    assert service.run_due(_FRIDAY_16) == 1
    assert len(template_calls) == 1
    assert template_calls[0].template_name == "weekly_review_de"
