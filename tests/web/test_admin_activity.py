"""Tests für den Admin-Aktivitäts-Endpoint."""

from __future__ import annotations

from typing import Any


def test_activity_smoke(client: Any, auth_headers: dict[str, str]) -> None:
    """Admin erhält die Aktivitäts-Struktur (auch bei leerer DB)."""
    resp = client.get("/api/admin/activity", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data["recent_notifications"], list)
    assert isinstance(data["recent_mails"], list)
    assert set(data["notification_counts_24h"]) >= {
        "sent",
        "failed",
        "skipped",
        "pending",
    }
    assert "total" in data["mail_counts_24h"]


def test_activity_forbidden_for_tenant(
    client: Any,
    tenant_owner_auth_headers: dict[str, str],
) -> None:
    """Mandanten haben keinen Zugriff auf die Plattform-Aktivität."""
    resp = client.get("/api/admin/activity", headers=tenant_owner_auth_headers)
    assert resp.status_code == 403
