"""Human-Review-API."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, g, jsonify, request

from web.middleware.auth_guard import require_auth
from web.schemas.review import ReviewApproveRequest, ReviewRejectRequest

review_bp = Blueprint("review", __name__, url_prefix="/api/review")


@review_bp.post("/approve")
@require_auth
def approve() -> tuple[Any, int]:
    """Freigabe eines Entwurfs (kein Auto-Versand)."""
    body = ReviewApproveRequest.model_validate(request.get_json(silent=True) or {})
    try:
        result = g.ctx.review_router.approve_draft(
            body.correlation_id,
            approved_body=body.approved_body,
        )
    except Exception as exc:
        return jsonify({"error": str(exc), "code": 400}), 400
    return jsonify({"status": "approved", "result_keys": list(result.keys())}), 200


@review_bp.post("/reject")
@require_auth
def reject() -> tuple[Any, int]:
    """Ablehnung eines Entwurfs."""
    body = ReviewRejectRequest.model_validate(request.get_json(silent=True) or {})
    try:
        result = g.ctx.review_router.reject_draft(
            body.correlation_id,
            reason=body.reason or None,
        )
    except Exception as exc:
        return jsonify({"error": str(exc), "code": 400}), 400
    return jsonify({"status": "rejected", "result_keys": list(result.keys())}), 200
