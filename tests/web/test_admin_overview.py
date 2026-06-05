"""Admin-Monitoring: Overview, Detail, Metrics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from tests.web.test_registration import _register_payload


def _approve_tenant(client: Any, auth_headers: dict[str, str], email: str) -> str:
    client.post("/api/auth/register", json=_register_payload(email=email))
    pending = client.get("/api/admin/accounts?status=pending", headers=auth_headers)
    tenant = next(i for i in pending.get_json()["items"] if i["contact_email"] == email)
    client.post(
        f"/api/admin/accounts/{tenant['id']}/approve",
        headers=auth_headers,
    )
    return str(tenant["id"])


def _seed_metric(
    app: Any,
    *,
    account_id: str,
    correlation_id: str,
    cost_usd: float,
    processed_at: datetime,
) -> None:
    ctx = app.extensions["ctx"]
    ctx.metrics_repo.record(
        correlation_id,
        cost_usd=cost_usd,
        prompt_tokens=100,
        completion_tokens=50,
        account_id=account_id,
    )
    ctx.metrics_repo._col.update_one(
        {"_id": correlation_id},
        {"$set": {"processed_at": processed_at.isoformat()}},
    )


def test_admin_overview_with_two_tenants(
    client: Any,
    auth_headers: dict[str, str],
    app: Any,
) -> None:
    """Overview aggregiert KPIs und Mandanten-Aktivität."""
    tenant_a = _approve_tenant(client, auth_headers, "overview-a@test.local")
    tenant_b = _approve_tenant(client, auth_headers, "overview-b@test.local")
    now = datetime.now(UTC)
    _seed_metric(
        app,
        account_id=tenant_a,
        correlation_id="mail-a-1",
        cost_usd=0.05,
        processed_at=now - timedelta(days=1),
    )
    _seed_metric(
        app,
        account_id=tenant_b,
        correlation_id="mail-b-1",
        cost_usd=0.02,
        processed_at=now - timedelta(days=20),
    )

    ctx = app.extensions["ctx"]
    mail_a = ctx.mail_connection_repo.get_or_create(tenant_a)
    mail_a.last_sync_at = now - timedelta(days=1)
    ctx.mail_connection_repo.save(mail_a)

    resp = client.get("/api/admin/overview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["active_accounts"] >= 2
    assert data["total_cost_usd_30d"] >= 0.07
    assert data["mails_processed_30d"] >= 2
    tenants = {t["account"]["id"]: t for t in data["tenants"]}
    assert tenants[tenant_a]["activity_status"] == "active"
    assert tenants[tenant_b]["activity_status"] == "idle"


def test_admin_account_detail_db_counts(
    client: Any,
    auth_headers: dict[str, str],
    app: Any,
) -> None:
    """Detail liefert DB-Counts und Benutzer."""
    account_id = _approve_tenant(client, auth_headers, "detail-db@test.local")
    ctx = app.extensions["ctx"]
    ctx.db["emails"].insert_one(
        {
            "_id": "e1",
            "account_id": account_id,
            "received_at": datetime.now(UTC).isoformat(),
        }
    )

    resp = client.get(
        f"/api/admin/accounts/{account_id}/detail",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["db_counts"]["emails"] == 1
    assert len(data["users"]) >= 1
    assert data["account"]["id"] == account_id


def test_admin_metrics_costs_cross_tenant(
    client: Any,
    auth_headers: dict[str, str],
    app: Any,
) -> None:
    """Cross-Tenant Kosten und Top-Mails."""
    tenant_a = _approve_tenant(client, auth_headers, "costs-a@test.local")
    _seed_metric(
        app,
        account_id=tenant_a,
        correlation_id="expensive-1",
        cost_usd=0.99,
        processed_at=datetime.now(UTC),
    )

    resp = client.get("/api/admin/metrics/costs?days=30", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_usd"] >= 0.99
    assert any(m["correlation_id"] == "expensive-1" for m in data["top_mails"])
    assert any(row["account_id"] == tenant_a for row in data["by_account"])


def test_admin_overview_forbidden_for_tenant(
    client: Any,
    tenant_owner_auth_headers: dict[str, str],
) -> None:
    """Mandanten dürfen Admin-Overview nicht aufrufen."""
    resp = client.get("/api/admin/overview", headers=tenant_owner_auth_headers)
    assert resp.status_code == 403


def test_admin_account_detail_not_found(
    client: Any,
    auth_headers: dict[str, str],
) -> None:
    resp = client.get(
        "/api/admin/accounts/unknown-id/detail",
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_admin_costs_total_matches_sum_by_account(
    client: Any,
    auth_headers: dict[str, str],
    app: Any,
) -> None:
    tenant_a = _approve_tenant(client, auth_headers, "costs-sum-a@test.local")
    tenant_b = _approve_tenant(client, auth_headers, "costs-sum-b@test.local")
    now = datetime.now(UTC)
    _seed_metric(
        app,
        account_id=tenant_a,
        correlation_id="sum-a",
        cost_usd=0.10,
        processed_at=now,
    )
    _seed_metric(
        app,
        account_id=tenant_b,
        correlation_id="sum-b",
        cost_usd=0.20,
        processed_at=now,
    )

    resp = client.get("/api/admin/metrics/costs?days=30", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    by_account_sum = sum(row["cost_usd"] for row in data["by_account"])
    assert data["total_usd"] == round(by_account_sum + data["unassigned_cost_usd"], 4)
    assert data["total_usd"] >= 0.30


def test_admin_costs_unassigned_bucket(
    client: Any,
    auth_headers: dict[str, str],
    app: Any,
) -> None:
    now = datetime.now(UTC)
    _seed_metric(
        app,
        account_id="orphan-acc",
        correlation_id="assigned-1",
        cost_usd=0.10,
        processed_at=now,
    )
    ctx = app.extensions["ctx"]
    ctx.metrics_repo.record(
        "unassigned-1",
        cost_usd=0.05,
        prompt_tokens=10,
        completion_tokens=5,
        account_id=None,
    )
    ctx.metrics_repo._col.update_one(
        {"_id": "unassigned-1"},
        {"$set": {"processed_at": now.isoformat(), "account_id": None}},
    )

    resp = client.get("/api/admin/metrics/costs?days=30", headers=auth_headers)
    data = resp.get_json()
    assert data["unassigned_cost_usd"] >= 0.05
    by_account_sum = sum(row["cost_usd"] for row in data["by_account"])
    assert data["total_usd"] == round(by_account_sum + data["unassigned_cost_usd"], 4)
