"""Tests für die DSGVO-Gastfunktionen (Auskunft, Löschung, Einwilligung)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.core.models.email import ProcessingState, StoredEmail

GUEST = "max.mustermann@example.com"


def _seed(email_repo: Any, account_id: str, cid: str, sender: str = GUEST) -> None:
    email_repo.upsert_by_message_id(
        StoredEmail(
            message_id=f"{cid}@test",
            from_address=sender,
            subject=f"Buchung {cid}",
            body_text="Daten",
            received_at=datetime.now(UTC),
            correlation_id=cid,
            processing_state=ProcessingState.CLASSIFIED,
            account_id=account_id,
        )
    )


def test_export_requires_auth(client: Any) -> None:
    assert client.get(f"/api/guests/{GUEST}/export").status_code == 401


def test_export_lists_guest_mails(
    client: Any, auth_headers: dict, tenant_account_id: str, email_repo: Any
) -> None:
    _seed(email_repo, tenant_account_id, "g-1")
    _seed(email_repo, tenant_account_id, "g-2")
    resp = client.get(f"/api/guests/{GUEST}/export", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["mail_count"] == 2
    assert data["email"] == GUEST


def test_consent_round_trip(
    client: Any, auth_headers: dict, tenant_account_id: str
) -> None:
    put = client.put(
        f"/api/guests/{GUEST}/consent",
        headers=auth_headers,
        json={"whatsapp_consent": True},
    )
    assert put.status_code == 200
    assert put.get_json()["whatsapp_consent"] is True
    assert put.get_json()["consent_at"]

    got = client.get(f"/api/guests/{GUEST}/consent", headers=auth_headers)
    assert got.get_json()["whatsapp_consent"] is True


def test_delete_removes_guest_data(
    client: Any, auth_headers: dict, tenant_account_id: str, email_repo: Any
) -> None:
    _seed(email_repo, tenant_account_id, "g-del-1")
    _seed(email_repo, tenant_account_id, "g-del-2")
    _seed(email_repo, tenant_account_id, "keep-1", sender="other@example.com")

    resp = client.delete(f"/api/guests/{GUEST}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["deleted"]["emails"] == 2

    after = client.get(f"/api/guests/{GUEST}/export", headers=auth_headers)
    assert after.get_json()["mail_count"] == 0
    # Andere Gäste bleiben unangetastet.
    other = client.get("/api/guests/other@example.com/export", headers=auth_headers)
    assert other.get_json()["mail_count"] == 1
