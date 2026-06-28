"""Human-Review-API."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, g, jsonify, request

from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.tenant import get_request_account_id, require_account
from backend.api.schemas.review import (
    ReviewApproveRequest,
    ReviewBulkApproveItem,
    ReviewBulkApproveRequest,
    ReviewBulkApproveResponse,
    ReviewCompleteRequest,
    ReviewQueueResponse,
    ReviewRejectRequest,
    ReviewTranslateRequest,
    ReviewTranslateResponse,
    ReviewUndoRequest,
)
from backend.api.services.review_actions_service import (
    complete_review,
    undo_auto_approval,
    whatsapp_preview,
)
from backend.api.services.review_queue_service import list_review_queue
from backend.api.services.review_translate import translate_draft
from backend.features.review.review_learning import learn_from_approved_review

review_bp = Blueprint("review", __name__, url_prefix="/api/review")


def _assert_tenant_owns_correlation(correlation_id: str) -> tuple[Any, int] | None:
    account_id = get_request_account_id()
    if not account_id:
        return jsonify({"error": "Account context required", "code": 403}), 403
    email = g.ctx.email_repo.get_by_correlation_id(
        correlation_id,
        account_id=account_id,
    )
    if email is None:
        return jsonify({"error": "Email not found", "code": 404}), 404
    return None


def _queue_response(queue: str) -> tuple[Any, int]:
    limit = min(max(int(request.args.get("limit", 50)), 1), 100)
    intent = request.args.get("intent") or None
    grounding_only = request.args.get("grounding", "").lower() in (
        "1",
        "true",
        "yes",
    )
    account_id = get_request_account_id()
    if not account_id:
        return jsonify({"error": "Account context required", "code": 403}), 403
    items = list_review_queue(
        g.ctx,
        account_id,
        queue=queue,
        limit=limit,
        intent=intent,
        grounding_only=grounding_only,
    )
    return (
        jsonify(ReviewQueueResponse(items=items, total=len(items)).model_dump()),
        200,
    )


@review_bp.get("/pending")
@require_auth
@require_account
def list_pending() -> tuple[Any, int]:
    """Ausstehende Entwürfe."""
    return _queue_response("pending")


@review_bp.get("/released")
@require_auth
@require_account
def list_released() -> tuple[Any, int]:
    """Freigegeben, noch nicht abgeschlossen."""
    return _queue_response("released")


@review_bp.get("/completed")
@require_auth
@require_account
def list_completed() -> tuple[Any, int]:
    """Abgeschlossene Reviews."""
    return _queue_response("completed")


@review_bp.get("/ground-zero")
@require_auth
@require_account
def list_ground_zero() -> tuple[Any, int]:
    """Offene Grounding-Fälle (pending oder freigegeben)."""
    limit = min(max(int(request.args.get("limit", 50)), 1), 100)
    intent = request.args.get("intent") or None
    account_id = get_request_account_id()
    if not account_id:
        return jsonify({"error": "Account context required", "code": 403}), 403
    items = list_review_queue(
        g.ctx,
        account_id,
        queue="pending",
        limit=limit,
        intent=intent,
        grounding_only=True,
    )
    return (
        jsonify(ReviewQueueResponse(items=items, total=len(items)).model_dump()),
        200,
    )


@review_bp.get("/whatsapp-preview/<correlation_id>")
@require_auth
@require_account
def preview_whatsapp(correlation_id: str) -> tuple[Any, int]:
    """WhatsApp-Template-Vorschau."""
    denied = _assert_tenant_owns_correlation(correlation_id)
    if denied:
        return denied
    account_id = get_request_account_id()
    assert account_id
    try:
        preview = whatsapp_preview(g.ctx, account_id, correlation_id)
    except Exception as exc:
        return jsonify({"error": str(exc), "code": 400}), 400
    return jsonify(preview.model_dump()), 200


@review_bp.post("/approve")
@require_auth
@require_account
def approve() -> tuple[Any, int]:
    """Freigabe eines Entwurfs (kein Auto-Versand)."""
    body = ReviewApproveRequest.model_validate(request.get_json(silent=True) or {})
    denied = _assert_tenant_owns_correlation(body.correlation_id)
    if denied:
        return denied
    account_id = get_request_account_id()
    assert account_id
    try:
        result = g.ctx.review_router.approve_draft(
            body.correlation_id,
            approved_body=body.approved_body,
        )
        learn_from_approved_review(
            g.ctx,
            account_id,
            body.correlation_id,
            body.approved_body,
        )
    except Exception as exc:
        return jsonify({"error": str(exc), "code": 400}), 400
    return jsonify({"status": "approved", "result_keys": list(result.keys())}), 200


@review_bp.post("/bulk-approve")
@require_auth
@require_account
def bulk_approve() -> tuple[Any, int]:
    """Sammel-Freigabe: gibt mehrere Entwürfe in einem Aufruf frei.

    Jede Correlation-ID wird auf Mandanten-Besitz geprüft; der gespeicherte
    Entwurf wird freigegeben (kein Auto-Versand). Fehler pro ID brechen die
    Aktion nicht ab, sondern werden im Ergebnis ausgewiesen.
    """
    body = ReviewBulkApproveRequest.model_validate(request.get_json(silent=True) or {})
    account_id = get_request_account_id()
    if not account_id:
        return jsonify({"error": "Account context required", "code": 403}), 403

    seen: set[str] = set()
    items: list[ReviewBulkApproveItem] = []
    approved = 0
    for correlation_id in body.correlation_ids:
        if not correlation_id or correlation_id in seen:
            continue
        seen.add(correlation_id)
        if _assert_tenant_owns_correlation(correlation_id) is not None:
            items.append(
                ReviewBulkApproveItem(
                    correlation_id=correlation_id,
                    status="not_found",
                    error="Email not found",
                )
            )
            continue
        try:
            g.ctx.review_router.approve_draft(correlation_id, approved_body=None)
            learn_from_approved_review(g.ctx, account_id, correlation_id, None)
            approved += 1
            items.append(
                ReviewBulkApproveItem(correlation_id=correlation_id, status="approved")
            )
        except Exception as exc:  # noqa: BLE001 - Einzelfehler nicht fatal
            items.append(
                ReviewBulkApproveItem(
                    correlation_id=correlation_id,
                    status="error",
                    error=str(exc),
                )
            )

    response = ReviewBulkApproveResponse(
        approved=approved,
        failed=len(items) - approved,
        items=items,
    )
    return jsonify(response.model_dump()), 200


@review_bp.post("/complete")
@require_auth
@require_account
def complete() -> tuple[Any, int]:
    """Review nach Freigabe abschließen."""
    body = ReviewCompleteRequest.model_validate(request.get_json(silent=True) or {})
    denied = _assert_tenant_owns_correlation(body.correlation_id)
    if denied:
        return denied
    account_id = get_request_account_id()
    assert account_id
    try:
        result = complete_review(g.ctx, account_id, body.correlation_id)
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": 400}), 400
    return jsonify(result), 200


@review_bp.post("/undo")
@require_auth
@require_account
def undo() -> tuple[Any, int]:
    """Macht eine Auto-Freigabe innerhalb von ~30 Sek rückgängig (zurück auf offen)."""
    body = ReviewUndoRequest.model_validate(request.get_json(silent=True) or {})
    denied = _assert_tenant_owns_correlation(body.correlation_id)
    if denied:
        return denied
    account_id = get_request_account_id()
    assert account_id
    error = undo_auto_approval(g.ctx, account_id, body.correlation_id)
    if error:
        return jsonify({"error": error, "code": 400}), 400
    return jsonify({"status": "reverted", "correlation_id": body.correlation_id}), 200


@review_bp.post("/translate")
@require_auth
@require_account
def translate() -> tuple[Any, int]:
    """Übersetzt den Entwurf in DE/EN für den Antwortsprachen-Umschalter."""
    body = ReviewTranslateRequest.model_validate(request.get_json(silent=True) or {})
    denied = _assert_tenant_owns_correlation(body.correlation_id)
    if denied:
        return denied
    account_id = get_request_account_id()
    assert account_id
    target = "en" if body.target_language.lower().startswith("en") else "de"
    translated = translate_draft(
        g.ctx, account_id, body.correlation_id, target, body.draft_body
    )
    return (
        jsonify(
            ReviewTranslateResponse(
                correlation_id=body.correlation_id,
                target_language=target,
                translated_body=translated,
            ).model_dump()
        ),
        200,
    )


@review_bp.post("/reject")
@require_auth
@require_account
def reject() -> tuple[Any, int]:
    """Ablehnung eines Entwurfs."""
    body = ReviewRejectRequest.model_validate(request.get_json(silent=True) or {})
    denied = _assert_tenant_owns_correlation(body.correlation_id)
    if denied:
        return denied
    try:
        result = g.ctx.review_router.reject_draft(
            body.correlation_id,
            reason=body.reason or None,
        )
    except Exception as exc:
        return jsonify({"error": str(exc), "code": 400}), 400
    return jsonify({"status": "rejected", "result_keys": list(result.keys())}), 200
