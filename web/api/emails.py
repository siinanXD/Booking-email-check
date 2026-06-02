"""E-Mail-Listen- und Detail-API."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, g, jsonify, request

from web.middleware.auth_guard import require_auth
from web.services.query_service import QueryService

emails_bp = Blueprint("emails", __name__, url_prefix="/api/emails")


@emails_bp.get("/")
@require_auth
def list_emails() -> tuple[Any, int]:
    """Paginierte E-Mail-Liste."""
    page = max(int(request.args.get("page", 1)), 1)
    limit = min(max(int(request.args.get("limit", 20)), 1), 100)
    svc = QueryService(g.ctx)
    result = svc.list_emails(
        status=request.args.get("status"),
        intent=request.args.get("intent"),
        platform=request.args.get("platform"),
        search=request.args.get("search"),
        page=page,
        limit=limit,
    )
    return jsonify(result.model_dump()), 200


@emails_bp.get("/<correlation_id>")
@require_auth
def email_detail(correlation_id: str) -> tuple[Any, int]:
    """Vollständiges Mail-Detail."""
    svc = QueryService(g.ctx)
    detail = svc.get_email_detail(correlation_id)
    if detail is None:
        return jsonify({"error": "Email not found", "code": 404}), 404
    return jsonify(detail.model_dump()), 200
