"""Unterkünfte: Historie, Empfänger, Vorschläge, Profile, Statistiken."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from flask import Blueprint, g, jsonify, request

from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.tenant import get_request_account_id, require_account
from backend.api.schemas.properties import (
    PropertyCreateRequest,
    PropertyRecipientsUpdateRequest,
    PropertyUpdateRequest,
)
from backend.api.services.property_crud_queries import (
    create_property,
    get_property_profile,
    list_properties,
    update_property_profile,
)
from backend.api.services.property_recipients_service import (
    get_recipients,
    save_recipients,
)
from backend.api.services.property_stats_queries import (
    property_history,
    property_year_stats,
)
from backend.api.services.property_suggestions_queries import property_suggestions

properties_bp = Blueprint("properties", __name__, url_prefix="/api/properties")


def _current_year() -> int:
    return datetime.now(UTC).year


def _parse_year_param() -> int:
    raw = request.args.get("year")
    if raw is None or not str(raw).strip():
        return _current_year()
    return int(raw)


@properties_bp.get("/history")
@require_auth
@require_account
def history() -> tuple[Any, int]:
    account_id = get_request_account_id()
    assert account_id
    limit = min(max(int(request.args.get("limit", 50)), 1), 100)
    prop = (request.args.get("property_name") or "").strip() or None
    result = property_history(g.ctx, account_id, property_name=prop, limit=limit)
    return jsonify(result.model_dump()), 200


@properties_bp.get("/recipients")
@require_auth
@require_account
def recipients_get() -> tuple[Any, int]:
    account_id = get_request_account_id()
    assert account_id
    return jsonify(get_recipients(g.ctx, account_id).model_dump()), 200


@properties_bp.put("/recipients")
@require_auth
@require_account
def recipients_put() -> tuple[Any, int]:
    account_id = get_request_account_id()
    assert account_id
    body = PropertyRecipientsUpdateRequest.model_validate(
        request.get_json(silent=True) or {}
    )
    result = save_recipients(g.ctx, account_id, body.items)
    return jsonify(result.model_dump()), 200


@properties_bp.get("/suggestions")
@require_auth
@require_account
def suggestions() -> tuple[Any, int]:
    account_id = get_request_account_id()
    assert account_id
    limit = min(max(int(request.args.get("limit", 20)), 1), 50)
    result = property_suggestions(g.ctx, account_id, limit=limit)
    return jsonify(result.model_dump()), 200


@properties_bp.get("")
@require_auth
@require_account
def property_list() -> tuple[Any, int]:
    account_id = get_request_account_id()
    assert account_id
    year = _parse_year_param()
    result = list_properties(g.ctx, account_id, year=year)
    return jsonify(result.model_dump()), 200


@properties_bp.post("")
@require_auth
@require_account
def property_create() -> tuple[Any, int]:
    account_id = get_request_account_id()
    assert account_id
    try:
        body = PropertyCreateRequest.model_validate(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    created = create_property(g.ctx, account_id, body)
    if created is None:
        return (
            jsonify({"error": "Unterkunft existiert bereits oder Name ungültig."}),
            409,
        )
    return jsonify(created.model_dump()), 201


@properties_bp.get("/<property_id>/stats")
@require_auth
@require_account
def property_stats(property_id: str) -> tuple[Any, int]:
    account_id = get_request_account_id()
    assert account_id
    year = _parse_year_param()
    result = property_year_stats(g.ctx, account_id, property_id, year=year)
    if result is None:
        return jsonify({"error": "Unterkunft nicht gefunden."}), 404
    return jsonify(result.model_dump()), 200


@properties_bp.get("/<property_id>")
@require_auth
@require_account
def property_get(property_id: str) -> tuple[Any, int]:
    account_id = get_request_account_id()
    assert account_id
    result = get_property_profile(g.ctx, account_id, property_id)
    if result is None:
        return jsonify({"error": "Unterkunft nicht gefunden."}), 404
    return jsonify(result.model_dump()), 200


@properties_bp.put("/<property_id>")
@require_auth
@require_account
def property_update(property_id: str) -> tuple[Any, int]:
    account_id = get_request_account_id()
    assert account_id
    try:
        body = PropertyUpdateRequest.model_validate(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    updated = update_property_profile(g.ctx, account_id, property_id, body)
    if updated is None:
        return jsonify({"error": "Unterkunft nicht gefunden oder Name vergeben."}), 404
    return jsonify(updated.model_dump()), 200
