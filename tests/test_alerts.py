"""Alert-Service."""

from __future__ import annotations

from models.response import GeneratedResponse
from observability.alerts import AlertService, AlertThresholds


def test_high_cost_alert(caplog) -> None:
    svc = AlertService(thresholds=AlertThresholds(max_cost_per_mail_usd=0.1))
    svc.check_cost_per_mail(0.5, "corr-alert-1")
    assert any("high_cost" in r.message for r in caplog.records)


def test_no_grounding_alert_when_grounded(caplog) -> None:
    """Negativfall: sauber gegroundete Antwort löst keinen Alert aus."""
    svc = AlertService()
    draft = GeneratedResponse(
        correlation_id="corr-ground-ok",
        body="Buchung AB100 bestätigt.",
        model="test",
        grounding_ok=True,
    )
    if not draft.grounding_ok:
        svc.check_grounding_suspect(draft.correlation_id)
    assert not any("grounding_suspect" in r.message for r in caplog.records)


def test_grounding_alert_when_not_grounded(caplog) -> None:
    svc = AlertService()
    draft = GeneratedResponse(
        correlation_id="corr-ground-bad",
        body="Buchung ZZ99999.",
        model="test",
        grounding_ok=False,
    )
    if not draft.grounding_ok:
        svc.check_grounding_suspect(draft.correlation_id)
    assert any("grounding_suspect" in r.message for r in caplog.records)
