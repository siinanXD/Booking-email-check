"""DSGVO-Gastfunktionen: Auskunft (Art. 15), Löschung (Art. 17), Einwilligung.

Ein „Gast" wird über seine E-Mail-Adresse identifiziert (``guest_id``). Alle
Operationen sind strikt Account-scoped.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote

from flask import Blueprint, g, jsonify, request

from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.roles import is_account_admin
from backend.api.middleware.tenant import get_request_account_id, require_account
from backend.api.schemas.guests import (
    GuestConsent,
    GuestConsentUpdate,
    GuestDeleteResponse,
    GuestExportResponse,
    GuestMailItem,
)

guests_bp = Blueprint("guests", __name__, url_prefix="/api/guests")

_CONSENT_COLLECTION = "guest_consent"


def _require_admin() -> tuple[Any, int] | None:
    if not is_account_admin(g.current_user.get("role")):
        return jsonify({"error": "Admin required", "code": 403}), 403
    return None


def _consent_id(account_id: str, email: str) -> str:
    return f"{account_id}:{email.strip().lower()}"


def _load_consent(account_id: str, email: str) -> GuestConsent:
    col = g.ctx.db[_CONSENT_COLLECTION]
    doc = col.find_one({"_id": _consent_id(account_id, email)})
    if not doc:
        return GuestConsent()
    return GuestConsent(
        whatsapp_consent=bool(doc.get("whatsapp_consent", False)),
        consent_at=doc.get("consent_at"),
    )


@guests_bp.get("/<guest_id>/export")
@require_auth
@require_account
def export_guest(guest_id: str) -> tuple[Any, int]:
    """Auskunft nach Art. 15: alle gespeicherten Daten zum Gast."""
    denied = _require_admin()
    if denied:
        return denied
    account_id = get_request_account_id()
    assert account_id
    email = unquote(guest_id)
    emails = g.ctx.email_repo.list_by_sender(email, account_id=account_id)
    mails = [
        GuestMailItem(
            correlation_id=e.correlation_id,
            subject=e.subject,
            received_at=e.received_at.isoformat() if e.received_at else None,
            intent=getattr(e, "effective_intent", None),
        )
        for e in emails
    ]
    response = GuestExportResponse(
        guest_id=guest_id,
        email=email,
        consent=_load_consent(account_id, email),
        mails=mails,
        mail_count=len(mails),
        generated_at=datetime.now(UTC).isoformat(),
    )
    return jsonify(response.model_dump()), 200


@guests_bp.delete("/<guest_id>")
@require_auth
@require_account
def delete_guest(guest_id: str) -> tuple[Any, int]:
    """Löschung nach Art. 17: entfernt Mails + abgeleitete Daten des Gastes."""
    denied = _require_admin()
    if denied:
        return denied
    account_id = get_request_account_id()
    assert account_id
    email = unquote(guest_id)

    mails_deleted, correlation_ids = g.ctx.email_repo.delete_by_sender(
        email, account_id=account_id
    )
    deleted: dict[str, int] = {"emails": mails_deleted}
    if correlation_ids:
        cid_filter = {"correlation_id": {"$in": correlation_ids}}
        for label, collection in (
            ("extractions", "extractions"),
            ("reviews", "reviews"),
            ("embeddings", "embeddings"),
        ):
            res = g.ctx.db[collection].delete_many(
                {**cid_filter, "account_id": account_id}
            )
            deleted[label] = int(res.deleted_count)
    consent_res = g.ctx.db[_CONSENT_COLLECTION].delete_one(
        {"_id": _consent_id(account_id, email)}
    )
    deleted["consent"] = int(consent_res.deleted_count)

    return (
        jsonify(GuestDeleteResponse(guest_id=guest_id, deleted=deleted).model_dump()),
        200,
    )


@guests_bp.get("/<guest_id>/consent")
@require_auth
@require_account
def get_consent(guest_id: str) -> tuple[Any, int]:
    """Liest die dokumentierte WhatsApp-Einwilligung."""
    account_id = get_request_account_id()
    assert account_id
    email = unquote(guest_id)
    return jsonify(_load_consent(account_id, email).model_dump()), 200


@guests_bp.put("/<guest_id>/consent")
@require_auth
@require_account
def set_consent(guest_id: str) -> tuple[Any, int]:
    """Dokumentiert/aktualisiert die WhatsApp-Einwilligung (Flag + Zeitstempel)."""
    denied = _require_admin()
    if denied:
        return denied
    account_id = get_request_account_id()
    assert account_id
    email = unquote(guest_id)
    body = GuestConsentUpdate.model_validate(request.get_json(silent=True) or {})
    now = datetime.now(UTC).isoformat()
    consent = GuestConsent(
        whatsapp_consent=body.whatsapp_consent,
        consent_at=now if body.whatsapp_consent else None,
    )
    g.ctx.db[_CONSENT_COLLECTION].update_one(
        {"_id": _consent_id(account_id, email)},
        {
            "$set": {
                "account_id": account_id,
                "email": email.strip().lower(),
                "whatsapp_consent": consent.whatsapp_consent,
                "consent_at": consent.consent_at,
            }
        },
        upsert=True,
    )
    return jsonify(consent.model_dump()), 200
