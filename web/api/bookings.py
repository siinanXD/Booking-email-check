"""Buchungsliste (Intent-Filter)."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, g, jsonify, request

from schemas.booking.taxonomy import BookingIntent
from web.middleware.auth_guard import require_auth
from web.services.query_service import QueryService

bookings_bp = Blueprint("bookings", __name__, url_prefix="/api/bookings")


@bookings_bp.get("/")
@require_auth
def list_bookings() -> tuple[Any, int]:
    """Neue Buchungen (intent=new_booking)."""
    page = max(int(request.args.get("page", 1)), 1)
    limit = min(max(int(request.args.get("limit", 20)), 1), 100)
    svc = QueryService(g.ctx)
    result = svc.list_emails(
        status=request.args.get("status"),
        intent=BookingIntent.NEW_BOOKING.value,
        platform=request.args.get("platform"),
        search=request.args.get("search"),
        page=page,
        limit=limit,
    )
    return jsonify(result.model_dump()), 200
