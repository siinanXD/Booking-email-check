"""Tests für Admin-Selbstschutz-Guards und Audit-Log."""

from __future__ import annotations

from typing import Any

from tests.web.test_registration import _register_payload


def test_cannot_suspend_own_account(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
) -> None:
    """Der Admin kann den eigenen Account nicht sperren."""
    resp = client.post(
        f"/api/admin/accounts/{tenant_account_id}/suspend", headers=auth_headers
    )
    assert resp.status_code == 403


def test_cannot_delete_own_account(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
) -> None:
    """Der Admin kann den eigenen Account nicht löschen."""
    resp = client.delete(
        f"/api/admin/accounts/{tenant_account_id}", headers=auth_headers
    )
    assert resp.status_code == 403


def _create_pending_account(client: Any, auth_headers: dict[str, str]) -> str:
    payload = _register_payload(email="audit-target@test.local")
    client.post("/api/auth/register", json=payload)
    pending = client.get("/api/admin/accounts?status=pending", headers=auth_headers)
    tenant = next(
        i for i in pending.get_json()["items"] if i["contact_email"] == payload["email"]
    )
    return str(tenant["id"])


def test_audit_log_records_approve(
    client: Any,
    auth_headers: dict[str, str],
) -> None:
    """Eine Freischaltung erscheint im Audit-Log."""
    account_id = _create_pending_account(client, auth_headers)
    approve = client.post(
        f"/api/admin/accounts/{account_id}/approve", headers=auth_headers
    )
    assert approve.status_code == 200

    resp = client.get("/api/admin/audit-log", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.get_json()["items"]
    matching = [
        e
        for e in items
        if e["action"] == "account.approve"
        and e["details"].get("account_id") == account_id
    ]
    assert len(matching) == 1
    assert matching[0]["user_id"]
