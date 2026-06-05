"""E-Mail-Listen- und Detail-API."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.tenant import require_account
from backend.api.services.api_helpers import tenant_query_service

emails_bp = Blueprint("emails", __name__, url_prefix="/api/emails")


@emails_bp.get("/")
@require_auth
@require_account
def list_emails() -> tuple[Any, int]:
    """Paginierte E-Mail-Liste."""
    page = max(int(request.args.get("page", 1)), 1)
    limit = min(max(int(request.args.get("limit", 20)), 1), 100)
    intents_raw = request.args.get("intents", "")
    intents = [s.strip() for s in intents_raw.split(",") if s.strip()] or None
    booking_related = request.args.get("booking_related", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    svc = tenant_query_service()
    workflow_slug = (request.args.get("workflow_slug") or "").strip() or None
    result = svc.list_emails(
        status=request.args.get("status"),
        intent=request.args.get("intent"),
        intents=intents,
        platform=request.args.get("platform"),
        search=request.args.get("search"),
        booking_related=booking_related,
        workflow_slug=workflow_slug,
        page=page,
        limit=limit,
        from_date=request.args.get("from_date"),
        to_date=request.args.get("to_date"),
    )
    return jsonify(result.model_dump()), 200


@emails_bp.get("/<correlation_id>/activity")
@require_auth
@require_account
def email_activity(correlation_id: str) -> tuple[Any, int]:
    """Arbeitsverlauf zu einer E-Mail."""
    svc = tenant_query_service()
    activity = svc.get_email_activity(correlation_id)
    if activity is None:
        return jsonify({"error": "Email not found", "code": 404}), 404
    return jsonify(activity.model_dump()), 200


@emails_bp.get("/<correlation_id>")
@require_auth
@require_account
def email_detail(correlation_id: str) -> tuple[Any, int]:
    """Vollständiges Mail-Detail."""
    svc = tenant_query_service()
    detail = svc.get_email_detail(correlation_id)
    if detail is None:
        return jsonify({"error": "Email not found", "code": 404}), 404
    return jsonify(detail.model_dump()), 200
