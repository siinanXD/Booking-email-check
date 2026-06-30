"""Web-Tests für die Putzplan-API."""

from __future__ import annotations

from datetime import date

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.features.cleaning.models import CleaningTask, CleaningTaskStatus
from backend.infrastructure.repositories.platform_settings_repository import (
    FEATURE_CLEANING_SCHEDULE,
    PlatformSettingsRecord,
)


def _enable(app: object, account_id: str) -> None:
    ctx = app.extensions["ctx"]  # type: ignore[attr-defined]
    ctx.platform_settings_repo.save(
        PlatformSettingsRecord(
            id=account_id, features={FEATURE_CLEANING_SCHEDULE: True}
        )
    )


def _seed_task(app: object, account_id: str) -> str:
    ctx = app.extensions["ctx"]  # type: ignore[attr-defined]
    task = CleaningTask(
        task_id="t-1",
        account_id=account_id,
        booking_number="BN-1",
        property_name="Loft A",
        guest_name="Max Muster",
        check_in=date(2026, 7, 5),
        check_out=date(2026, 7, 10),
        cleaning_date=date(2026, 7, 10),
        status=CleaningTaskStatus.UNASSIGNED,
    )
    ctx.cleaning_task_repo.upsert(task, account_id=account_id)
    return task.task_id


def test_feature_off_returns_403(
    client: object, auth_headers: dict[str, str], tenant_account_id: str
) -> None:
    """Ohne Freischaltung liefert die API 403."""
    resp = client.get("/api/cleaning/partners", headers=auth_headers)  # type: ignore[attr-defined]
    assert resp.status_code == 403


def test_partner_crud(
    app: object,
    client: object,
    auth_headers: dict[str, str],
    tenant_account_id: str,
) -> None:
    """Putzpartner anlegen, aktualisieren, deaktivieren."""
    _enable(app, tenant_account_id)
    created = client.post(  # type: ignore[attr-defined]
        "/api/cleaning/partners",
        headers=auth_headers,
        json={
            "name": "CleanCo",
            "phone": "+491700000000",
            "property_names": ["Loft A"],
        },
    )
    assert created.status_code == 201
    partner_id = created.get_json()["partner_id"]

    listed = client.get("/api/cleaning/partners", headers=auth_headers)  # type: ignore[attr-defined]
    assert listed.status_code == 200
    assert listed.get_json()["items"][0]["name"] == "CleanCo"

    updated = client.put(  # type: ignore[attr-defined]
        f"/api/cleaning/partners/{partner_id}",
        headers=auth_headers,
        json={"contact_person": "Anna"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["contact_person"] == "Anna"

    deleted = client.delete(  # type: ignore[attr-defined]
        f"/api/cleaning/partners/{partner_id}", headers=auth_headers
    )
    assert deleted.status_code == 200


def test_invalid_phone_is_rejected(
    app: object,
    client: object,
    auth_headers: dict[str, str],
    tenant_account_id: str,
) -> None:
    """Ungültige Telefonnummer → 422."""
    _enable(app, tenant_account_id)
    resp = client.post(  # type: ignore[attr-defined]
        "/api/cleaning/partners",
        headers=auth_headers,
        json={"name": "X", "phone": "0170123"},
    )
    assert resp.status_code == 422


def test_tasks_list_and_patch(
    app: object,
    client: object,
    auth_headers: dict[str, str],
    tenant_account_id: str,
) -> None:
    """Auftrag auflisten und manuell auf erledigt setzen."""
    _enable(app, tenant_account_id)
    task_id = _seed_task(app, tenant_account_id)

    listed = client.get("/api/cleaning/tasks", headers=auth_headers)  # type: ignore[attr-defined]
    assert listed.status_code == 200
    assert listed.get_json()["total"] == 1

    patched = client.patch(  # type: ignore[attr-defined]
        f"/api/cleaning/tasks/{task_id}",
        headers=auth_headers,
        json={"status": "done"},
    )
    assert patched.status_code == 200
    assert patched.get_json()["status"] == "done"


def test_tasks_export_xlsx(
    app: object,
    client: object,
    auth_headers: dict[str, str],
    tenant_account_id: str,
) -> None:
    """Excel-Export liefert eine .xlsx-Datei."""
    _enable(app, tenant_account_id)
    _seed_task(app, tenant_account_id)
    resp = client.get("/api/cleaning/tasks/export", headers=auth_headers)  # type: ignore[attr-defined]
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["Content-Type"]
    assert resp.data[:2] == b"PK"  # xlsx = zip


def test_tasks_export_ics(
    app: object,
    client: object,
    auth_headers: dict[str, str],
    tenant_account_id: str,
) -> None:
    """iCal-Export liefert eine .ics-Datei."""
    _enable(app, tenant_account_id)
    _seed_task(app, tenant_account_id)
    resp = client.get("/api/cleaning/tasks/export.ics", headers=auth_headers)  # type: ignore[attr-defined]
    assert resp.status_code == 200
    assert "text/calendar" in resp.headers["Content-Type"]
    assert resp.data.startswith(b"BEGIN:VCALENDAR")


def test_status_history_exposed(
    app: object,
    client: object,
    auth_headers: dict[str, str],
    tenant_account_id: str,
) -> None:
    """Statusänderungen erscheinen im status_history der Auftragsliste."""
    _enable(app, tenant_account_id)
    task_id = _seed_task(app, tenant_account_id)
    client.patch(  # type: ignore[attr-defined]
        f"/api/cleaning/tasks/{task_id}",
        headers=auth_headers,
        json={"status": "done"},
    )
    listed = client.get("/api/cleaning/tasks", headers=auth_headers)  # type: ignore[attr-defined]
    history = listed.get_json()["items"][0]["status_history"]
    assert any(ev["status"] == "done" for ev in history)


def test_dashboard_counts_open_cleaning_tasks(
    app: object,
    client: object,
    auth_headers: dict[str, str],
    tenant_account_id: str,
) -> None:
    """Offene Putzaufträge erscheinen im Dashboard-Zähler."""
    _enable(app, tenant_account_id)
    _seed_task(app, tenant_account_id)
    stats = client.get("/api/dashboard/stats", headers=auth_headers)  # type: ignore[attr-defined]
    assert stats.status_code == 200
    assert stats.get_json()["nav_cleaning_tasks"] >= 1


def test_admin_toggle_enables_and_unblocks_api(
    client: object, auth_headers: dict[str, str], tenant_account_id: str
) -> None:
    """Plattform-Admin schaltet das Feature frei → Tenant-API liefert nicht mehr 403."""
    blocked = client.get("/api/cleaning/partners", headers=auth_headers)  # type: ignore[attr-defined]
    assert blocked.status_code == 403
    toggled = client.put(  # type: ignore[attr-defined]
        f"/api/admin/accounts/{tenant_account_id}/features",
        headers=auth_headers,
        json={"feature": "cleaning_schedule", "enabled": True},
    )
    assert toggled.status_code == 200
    assert toggled.get_json()["features"]["cleaning_schedule"] is True
    ok = client.get("/api/cleaning/partners", headers=auth_headers)  # type: ignore[attr-defined]
    assert ok.status_code == 200


def test_admin_unknown_feature_rejected(
    client: object, auth_headers: dict[str, str], tenant_account_id: str
) -> None:
    """Unbekanntes Feature → 422."""
    resp = client.put(  # type: ignore[attr-defined]
        f"/api/admin/accounts/{tenant_account_id}/features",
        headers=auth_headers,
        json={"feature": "does_not_exist", "enabled": True},
    )
    assert resp.status_code == 422


def test_admin_enable_triggers_backfill(
    app: object, client: object, auth_headers: dict[str, str], tenant_account_id: str
) -> None:
    """Beim Aktivieren werden zukünftige Buchungen als Aufträge übernommen."""
    ctx = app.extensions["ctx"]  # type: ignore[attr-defined]
    ctx.extraction_repo.save(
        "corr-bf",
        "msg-bf",
        BookingExtraction(
            intent=BookingIntent.NEW_BOOKING,
            booking_number="BF-1",
            property_name="Loft A",
            check_out=date(2099, 1, 1),
        ),
        account_id=tenant_account_id,
    )
    resp = client.put(  # type: ignore[attr-defined]
        f"/api/admin/accounts/{tenant_account_id}/features",
        headers=auth_headers,
        json={"feature": "cleaning_schedule", "enabled": True},
    )
    assert resp.status_code == 200
    assert resp.get_json()["backfilled"] >= 1
    tasks = client.get("/api/cleaning/tasks", headers=auth_headers)  # type: ignore[attr-defined]
    assert tasks.get_json()["total"] >= 1
