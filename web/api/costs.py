"""API-Kosten-Endpoints."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, g, jsonify, request

from web.middleware.auth_guard import require_auth
from web.services.query_service import QueryService

costs_bp = Blueprint("costs", __name__, url_prefix="/api/costs")


@costs_bp.get("/")
@require_auth
def costs() -> tuple[Any, int]:
    """Kosten-Aggregation."""
    svc = QueryService(g.ctx)
    result = svc.costs(
        from_date=request.args.get("from_date"),
        to_date=request.args.get("to_date"),
        group_by=request.args.get("group_by", "day"),
    )
    return jsonify(result.model_dump()), 200
