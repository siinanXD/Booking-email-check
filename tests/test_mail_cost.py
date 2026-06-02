"""Aggregierte Kosten pro Mail."""

from __future__ import annotations

from observability.alerts import AlertService, AlertThresholds
from observability.mail_cost import MailCostTracker
from services.llm_types import LLMCompletion


def test_finalize_aggregates_tokens_single_alert(caplog) -> None:
    alerts = AlertService(thresholds=AlertThresholds(max_cost_per_mail_usd=0.1))
    tracker = MailCostTracker(cost_per_1k_tokens_usd=0.1, alerts=alerts)
    completion = LLMCompletion(text="x", prompt_tokens=500, completion_tokens=500)
    tracker.add("corr-cost-1", completion)
    tracker.add("corr-cost-1", completion)
    cost = tracker.finalize("corr-cost-1")
    assert abs(cost - 0.2) < 0.001
    high_cost_msgs = [r for r in caplog.records if "high_cost" in r.message]
    assert len(high_cost_msgs) == 1


def test_finalize_no_alert_below_threshold(caplog) -> None:
    tracker = MailCostTracker(
        cost_per_1k_tokens_usd=0.002,
        alerts=AlertService(thresholds=AlertThresholds(max_cost_per_mail_usd=1.0)),
    )
    tracker.add(
        "corr-low",
        LLMCompletion(text="a", prompt_tokens=10, completion_tokens=10),
    )
    tracker.finalize("corr-low")
    assert not any("high_cost" in r.message for r in caplog.records)
