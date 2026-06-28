"""Round-Trip-Test: Auto-Freigabe-Konfiguration über die Settings-API."""

from __future__ import annotations

from typing import Any


def test_auto_approve_defaults(client: Any, auth_headers: dict) -> None:
    resp = client.get("/api/settings", headers=auth_headers)
    assert resp.status_code == 200
    auto = resp.get_json()["auto_approve"]
    assert auto["enabled"] is False
    assert auto["threshold"] == 97


def test_auto_approve_round_trip(client: Any, auth_headers: dict) -> None:
    resp = client.put(
        "/api/settings",
        headers=auth_headers,
        json={
            "auto_approve": {
                "enabled": True,
                "threshold": 95,
                "per_intent": {"booking": True, "cancellation": True},
            }
        },
    )
    assert resp.status_code == 200
    auto = resp.get_json()["auto_approve"]
    assert auto["enabled"] is True
    assert auto["threshold"] == 95
    assert auto["per_intent"]["booking"] is True
    assert auto["per_intent"]["cancellation"] is True
    # Nicht gesetzte Intents werden mit False aufgefüllt.
    assert auto["per_intent"]["inquiry"] is False
    assert auto["per_intent"]["change"] is False


def test_auto_approve_threshold_validation(client: Any, auth_headers: dict) -> None:
    resp = client.put(
        "/api/settings",
        headers=auth_headers,
        json={"auto_approve": {"enabled": True, "threshold": 50}},
    )
    assert resp.status_code == 422
