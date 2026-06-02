"""Kosten-API-Tests."""

from __future__ import annotations

from typing import Any

from repositories.mail_metrics_repository import MailMetricsRepository


def test_costs_empty(client: Any, auth_headers: dict[str, str]) -> None:
    """Leere Metriken → leere Serie."""
    resp = client.get("/api/costs/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_usd"] == 0.0
    assert isinstance(data["series"], list)


def test_costs_with_metric(
    client: Any,
    auth_headers: dict[str, str],
    mock_db: object,
) -> None:
    """Gespeicherte Metrik erscheint in der Antwort."""
    metrics = MailMetricsRepository(mock_db)  # type: ignore[arg-type]
    metrics.record(
        "corr-cost",
        cost_usd=0.05,
        prompt_tokens=100,
        completion_tokens=50,
    )
    resp = client.get("/api/costs/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["total_usd"] >= 0.0
