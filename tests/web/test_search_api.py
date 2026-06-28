"""Tests für die globale Suche."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.core.models.email import ProcessingState, StoredEmail


def _seed_mail(email_repo: Any, account_id: str, subject: str, cid: str) -> None:
    email_repo.upsert_by_message_id(
        StoredEmail(
            message_id=f"{cid}@test",
            from_address="gast@example.com",
            subject=subject,
            body_text="hallo",
            received_at=datetime.now(UTC),
            correlation_id=cid,
            processing_state=ProcessingState.CLASSIFIED,
            account_id=account_id,
        )
    )


def test_search_requires_auth(client: Any) -> None:
    assert client.get("/api/search?q=villa").status_code == 401


def test_short_query_returns_empty_groups(client: Any, auth_headers: dict) -> None:
    resp = client.get("/api/search?q=v", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == {"bookings": [], "properties": [], "mails": []}


def test_search_finds_mail_by_subject(
    client: Any,
    auth_headers: dict,
    tenant_account_id: str,
    email_repo: Any,
) -> None:
    _seed_mail(
        email_repo, tenant_account_id, "Villa Sonnenhof Anfrage", "corr-search-1"
    )
    resp = client.get("/api/search?q=villa", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    titles = [hit["title"] for hit in data["mails"]]
    assert any("Villa Sonnenhof" in t for t in titles)
    assert all("href" in hit for hit in data["mails"])


def test_search_isolated_by_account(
    client: Any,
    auth_headers: dict,
    tenant_account_id: str,
    email_repo: Any,
) -> None:
    _seed_mail(email_repo, "other-account", "Geheime Villa", "corr-other-1")
    resp = client.get("/api/search?q=geheime", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["mails"] == []
