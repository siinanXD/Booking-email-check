"""Support-Tickets API."""

from __future__ import annotations

from typing import Any

from tests.web.test_registration import _register_payload


def _approve_and_login(
    client: Any,
    auth_headers: dict[str, str],
    email: str,
) -> dict[str, str]:
    client.post("/api/auth/register", json=_register_payload(email=email))
    pending = client.get("/api/admin/accounts?status=pending", headers=auth_headers)
    tenant = next(i for i in pending.get_json()["items"] if i["contact_email"] == email)
    client.post(
        f"/api/admin/accounts/{tenant['id']}/approve",
        headers=auth_headers,
    )
    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "secure-pass"},
    )
    token = login.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_tenant_create_and_list_ticket(
    client: Any,
    auth_headers: dict[str, str],
) -> None:
    tenant_headers = _approve_and_login(
        client, auth_headers, "support-tenant@test.local"
    )
    resp = client.post(
        "/api/support/tickets",
        headers=tenant_headers,
        json={
            "message": "Hilfe bei Mail-Anbindung",
            "urgency": "high",
            "subject": "Postfach",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["urgency"] == "high"
    assert data["status"] == "open"

    list_resp = client.get("/api/support/tickets", headers=tenant_headers)
    assert list_resp.status_code == 200
    items = list_resp.get_json()["items"]
    assert len(items) >= 1
    assert items[0]["ticket_id"] == data["ticket_id"]


def test_admin_list_and_patch_ticket(
    client: Any,
    auth_headers: dict[str, str],
) -> None:
    tenant_headers = _approve_and_login(
        client, auth_headers, "support-admin@test.local"
    )
    create = client.post(
        "/api/support/tickets",
        headers=tenant_headers,
        json={"message": "Test", "urgency": "critical"},
    )
    ticket_id = create.get_json()["ticket_id"]

    admin_list = client.get("/api/admin/support/tickets", headers=auth_headers)
    assert admin_list.status_code == 200
    items = admin_list.get_json()["items"]
    assert any(i["ticket_id"] == ticket_id for i in items)

    patch = client.patch(
        f"/api/admin/support/tickets/{ticket_id}",
        headers=auth_headers,
        json={"status": "in_progress", "admin_note": "Wird geprüft"},
    )
    assert patch.status_code == 200
    assert patch.get_json()["status"] == "in_progress"
    assert patch.get_json()["admin_note"] == "Wird geprüft"


def test_whatsapp_skipped_when_disabled(
    client: Any,
    auth_headers: dict[str, str],
) -> None:
    tenant_headers = _approve_and_login(client, auth_headers, "support-skip@test.local")
    resp = client.post(
        "/api/support/tickets",
        headers=tenant_headers,
        json={"message": "Ohne WhatsApp", "urgency": "normal"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["whatsapp_notify_status"] == "skipped"
