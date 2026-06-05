"""Properties-API-Tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.taxonomy import BookingIntent
from backend.core.models.email import ProcessingState, StoredEmail
from backend.core.models.entities import Property
from backend.infrastructure.repositories.extraction_repository import (
    ExtractionRepository,
)
from backend.infrastructure.repositories.property_repository import PropertyRepository


def test_property_recipients_roundtrip(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
) -> None:
    put_resp = client.put(
        "/api/properties/recipients",
        json={
            "items": [
                {"property_name": "Haus A", "phones": ["+491701234567"]},
            ]
        },
        headers=auth_headers,
    )
    assert put_resp.status_code == 200
    get_resp = client.get("/api/properties/recipients", headers=auth_headers)
    assert get_resp.status_code == 200
    data = get_resp.get_json()
    assert any(i["property_name"] == "Haus A" for i in data["items"])


def test_property_suggestions_empty_ok(
    client: Any,
    auth_headers: dict[str, str],
) -> None:
    resp = client.get("/api/properties/suggestions", headers=auth_headers)
    assert resp.status_code == 200
    assert "items" in resp.get_json()


def test_property_create_list_profile(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
) -> None:
    create_resp = client.post(
        "/api/properties",
        json={"name": "Ferienwohnung See", "from_suggestion": True},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    created = create_resp.get_json()
    property_id = created["property_id"]
    assert created["name"] == "Ferienwohnung See"
    assert created["whatsapp_phones"] == []

    list_resp = client.get("/api/properties", headers=auth_headers)
    assert list_resp.status_code == 200
    items = list_resp.get_json()["items"]
    assert any(i["property_id"] == property_id for i in items)

    get_resp = client.get(f"/api/properties/{property_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.get_json()["name"] == "Ferienwohnung See"

    dup_resp = client.post(
        "/api/properties",
        json={"name": "Ferienwohnung See"},
        headers=auth_headers,
    )
    assert dup_resp.status_code == 409


def test_property_update_profile(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
) -> None:
    create_resp = client.post(
        "/api/properties",
        json={"name": "Haus B"},
        headers=auth_headers,
    )
    property_id = create_resp.get_json()["property_id"]

    put_resp = client.put(
        f"/api/properties/{property_id}",
        json={
            "location": "München",
            "contact_name": "Maria",
            "contact_phone": "+491701234567",
            "contact_email": "maria@example.com",
            "notes": "Hintereingang",
            "whatsapp_phones": ["+491709876543"],
        },
        headers=auth_headers,
    )
    assert put_resp.status_code == 200
    updated = put_resp.get_json()
    assert updated["location"] == "München"
    assert updated["contact_name"] == "Maria"
    assert updated["whatsapp_phones"] == ["+491709876543"]

    bad_phone = client.put(
        f"/api/properties/{property_id}",
        json={"contact_phone": "01701234567"},
        headers=auth_headers,
    )
    assert bad_phone.status_code == 422


def test_property_year_stats(
    client: Any,
    auth_headers: dict[str, str],
    tenant_account_id: str,
    mock_db: Any,
    email_repo: Any,
    extraction_repo: ExtractionRepository,
) -> None:
    prop_repo = PropertyRepository(mock_db)
    prop = Property(
        property_id="prop_test_stats",
        name="Alpenchalet",
        account_id=tenant_account_id,
    )
    prop_repo.upsert(prop, account_id=tenant_account_id)

    email = StoredEmail(
        message_id="m-stats@test",
        from_address="booking@beds24.com",
        subject="Buchung: Alpenchalet",
        body_text="Buchung bestätigt",
        received_at=datetime(2026, 6, 1, tzinfo=UTC),
        correlation_id="corr-stats-1",
        processing_state=ProcessingState.PENDING_REVIEW,
        updated_at=datetime.now(UTC),
        account_id=tenant_account_id,
        platform="beds24",
    )
    email_repo.upsert_by_message_id(email)
    extraction_repo.save(
        "corr-stats-1",
        "m-stats@test",
        BookingExtraction(
            intent=BookingIntent.NEW_BOOKING,
            property_name="Alpenchalet",
            check_in=date(2026, 6, 10),
            check_out=date(2026, 6, 15),
            price=500.0,
            booking_number="B-100",
        ),
        account_id=tenant_account_id,
    )

    stats_resp = client.get(
        f"/api/properties/{prop.property_id}/stats?year=2026",
        headers=auth_headers,
    )
    assert stats_resp.status_code == 200
    stats = stats_resp.get_json()
    assert stats["booked_days"] == 5
    assert stats["revenue"] == 500.0
    assert stats["booking_count"] == 1
    assert stats["incomplete_data_count"] == 0

    list_resp = client.get("/api/properties?year=2026", headers=auth_headers)
    assert list_resp.status_code == 200
    row = next(
        i for i in list_resp.get_json()["items"] if i["property_id"] == prop.property_id
    )
    assert row["stats"]["booked_days"] == 5
