"""Das Putzplan-Gate muss für Task-Erzeugung und API dieselbe Wahrheit liefern.

Regression: `CleaningScheduleService.is_enabled` fragte nur die
platform_settings, die API dagegen die Entitlements (Plan-Features ∪
Admin-Toggles). Ein Pro-Account ohne Admin-Toggle sah damit eine
Putzplan-Oberfläche, für die nie Aufträge entstanden.
"""

from __future__ import annotations

import pytest

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.features.billing.plans import FEATURE_CLEANING_SCHEDULE
from backend.features.cleaning.service import CleaningScheduleService
from backend.infrastructure.repositories.cleaning_partner_repository import (
    CleaningPartnerRepository,
)
from backend.infrastructure.repositories.cleaning_task_repository import (
    CleaningTaskRepository,
)
from backend.infrastructure.repositories.mongo import Db
from backend.infrastructure.repositories.platform_settings_repository import (
    PlatformSettingsRepository,
)

ACCOUNT = "acc-1"


class FakeEntitlements:
    """Minimaler Stand-in für den EntitlementService."""

    def __init__(self, features: set[str]) -> None:
        self.features = features

    def effective_features(self, account_id: str) -> set[str]:
        return self.features


@pytest.fixture
def build(mock_db: Db):  # type: ignore[no-untyped-def]
    """Baut den Service mit optionalem Entitlement-Stand-in."""

    def _build(entitlements: FakeEntitlements | None) -> CleaningScheduleService:
        return CleaningScheduleService(
            CleaningPartnerRepository(mock_db),
            CleaningTaskRepository(mock_db),
            PlatformSettingsRepository(mock_db),
            None,
            entitlements,  # type: ignore[arg-type]
        )

    return _build


def test_plan_feature_schaltet_task_erzeugung_frei(build) -> None:  # type: ignore[no-untyped-def]
    """Pro/Business bringen den Putzplan per Plan mit — ohne Admin-Toggle."""
    service = build(FakeEntitlements({FEATURE_CLEANING_SCHEDULE}))
    assert service.is_enabled(ACCOUNT) is True


def test_ohne_feature_kein_task(build) -> None:  # type: ignore[no-untyped-def]
    service = build(FakeEntitlements(set()))
    assert service.is_enabled(ACCOUNT) is False


def test_ohne_account_kein_task(build) -> None:  # type: ignore[no-untyped-def]
    service = build(FakeEntitlements({FEATURE_CLEANING_SCHEDULE}))
    assert service.is_enabled(None) is False


def test_fallback_auf_platform_settings_ohne_entitlements(build) -> None:  # type: ignore[no-untyped-def]
    """Ohne Entitlement-Service bleibt das alte Verhalten (Tests, Skripte)."""
    service = build(None)
    assert service.is_enabled(ACCOUNT) is False


def test_plan_feature_erzeugt_wirklich_einen_task(build) -> None:  # type: ignore[no-untyped-def]
    """Das Gate ist der einzige Unterschied — der Task muss entstehen."""
    service = build(FakeEntitlements({FEATURE_CLEANING_SCHEDULE}))
    extraction = BookingExtraction(
        guest_name="Coosemans",
        property_name="Münzbach Ferienzimmer",
        check_in="2026-07-17",
        check_out="2026-07-18",
        booking_number="89790382",
    )
    task = service.process_booking_event("corr-1", extraction, account_id=ACCOUNT)
    assert task is not None
    assert task.cleaning_date is not None
    assert task.cleaning_date.isoformat() == "2026-07-18"
