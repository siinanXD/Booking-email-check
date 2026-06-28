"""Quelldaten-Widerspruch im Workflow → Eskalation + source_flags, kein Auto-Send."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.infrastructure.repositories.platform_settings_repository import (
    AutoApproveSettings,
    PlatformSettingsRecord,
)


def _run_conflict(ctx: Any, account_id: str) -> str:
    from backend.core.models.email import IncomingEmail

    payload = IncomingEmail(
        message_id="m-conflict-1",
        from_address="bookings@beds24.com",
        # Betreff nennt Nr. 3, Body nennt Nr. 1 → Widerspruch in der Quelle.
        subject="Neue Buchung Münzbach Ferienzimmer Zimmer Nr. 3 AB123",
        body_text=(
            "Münzbach Ferienzimmer\nZimmer Nr. 1\nBuchung AB123\n"
            "Email: gast@guest.booking.com\n"
        ),
        received_at=datetime.now(UTC),
        platform="beds24",
        account_id=account_id,
    )
    ctx.workflow.run(payload, thread_id=payload.correlation_id)
    return payload.correlation_id


def test_room_conflict_escalates_and_flags(app: object, tenant_account_id: str) -> None:
    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    cid = _run_conflict(ctx, tenant_account_id)
    record = ctx.review_repo.get(cid, account_id=tenant_account_id)
    assert record is not None
    assert record.escalated is True
    assert any("Zimmer widersprüchlich" in flag for flag in record.source_flags)


def test_conflict_blocks_auto_approve(app: object, tenant_account_id: str) -> None:
    ctx = app.extensions["ctx"]  # type: ignore[union-attr]
    record_settings = ctx.platform_settings_repo.get(
        tenant_account_id
    ) or PlatformSettingsRecord(id=tenant_account_id)
    record_settings.auto_approve = AutoApproveSettings(
        enabled=True,
        threshold=90,
        per_intent={
            "booking": True,
            "cancellation": False,
            "inquiry": False,
            "change": False,
        },
    )
    ctx.platform_settings_repo.save(record_settings)

    cid = _run_conflict(ctx, tenant_account_id)
    record = ctx.review_repo.get(cid, account_id=tenant_account_id)
    assert record is not None
    # Trotz aktivierter Auto-Freigabe: widersprüchliche Quelle wird NICHT gesendet.
    assert record.auto_approved is False
    assert record.review_status == "pending"
    assert record.escalated is True
