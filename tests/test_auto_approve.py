"""Unit-Tests für die Auto-Freigabe-Entscheidung."""

from __future__ import annotations

import pytest

from backend.features.review.auto_approve import (
    auto_approve_key,
    normalize_confidence,
    should_auto_approve,
)
from backend.infrastructure.repositories.platform_settings_repository import (
    AutoApproveSettings,
)


def _settings(**kw: object) -> AutoApproveSettings:
    base: dict[str, object] = {
        "enabled": True,
        "threshold": 97,
        "per_intent": {
            "booking": True,
            "cancellation": False,
            "inquiry": False,
            "change": False,
        },
    }
    base.update(kw)
    return AutoApproveSettings.model_validate(base)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.97, 97.0), (97, 97.0), (1.0, 100.0), (None, 0.0), (150, 100.0)],
)
def test_normalize_confidence(value: object, expected: float) -> None:
    assert normalize_confidence(value) == expected  # type: ignore[arg-type]


def test_intent_mapping() -> None:
    assert auto_approve_key("new_booking") == "booking"
    assert auto_approve_key("guest_inquiry") == "inquiry"
    assert auto_approve_key("cancellation") == "cancellation"
    assert auto_approve_key("change") == "change"
    assert auto_approve_key("spam") is None
    assert auto_approve_key(None) is None


def test_auto_approve_happy_path() -> None:
    assert should_auto_approve(0.98, "new_booking", _settings()) is True


def test_below_threshold_blocks() -> None:
    assert should_auto_approve(0.96, "new_booking", _settings(threshold=97)) is False


def test_disabled_intent_blocks() -> None:
    assert should_auto_approve(1.0, "cancellation", _settings()) is False


def test_master_switch_off_blocks() -> None:
    assert should_auto_approve(1.0, "new_booking", _settings(enabled=False)) is False


def test_unknown_intent_blocks() -> None:
    assert should_auto_approve(1.0, "spam", _settings()) is False


def test_escalation_rule() -> None:
    from backend.ai.workflows.nodes.pipeline_review import PipelineReviewMixin

    # Beschwerden eskalieren immer; niedrige Konfidenz ebenfalls.
    assert PipelineReviewMixin._should_escalate("complaint", 1.0) is True
    assert PipelineReviewMixin._should_escalate("new_booking", 0.3) is True
    assert PipelineReviewMixin._should_escalate("new_booking", 0.9) is False
