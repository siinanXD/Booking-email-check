"""Putzplan-API (Tenant): Putzpartner-CRUD, Auftragsliste, Excel-Export."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from flask import Blueprint, Response, g, jsonify, request

from backend.api.middleware.auth_guard import require_auth
from backend.api.middleware.tenant import get_request_account_id, require_account
from backend.api.schemas.cleaning import (
    PartnerCreateRequest,
    PartnerUpdateRequest,
    TaskUpdateRequest,
)
from backend.api.services.cleaning_queries import (
    create_partner,
    deactivate_partner,
    export_tasks_xlsx,
    feature_enabled,
    list_partners,
    list_tasks,
    update_partner,
    update_task,
)

cleaning_bp = Blueprint("cleaning", __name__, url_prefix="/api/cleaning")

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _account_id() -> str:
    account_id = get_request_account_id()
    assert account_id
    return account_id


def _gate() -> tuple[Any, int] | None:
    """403, wenn das Putzplan-Feature für den Account nicht aktiv ist."""
    if not feature_enabled(g.ctx, _account_id()):
        return jsonify({"error": "Feature not enabled", "code": 403}), 403
    return None


def _parse_date(raw: str | None) -> date | None:
    if not raw or not raw.strip():
        return None
    return date.fromisoformat(raw.strip())


def _filters() -> dict[str, Any]:
    return {
        "status": (request.args.get("status") or "").strip() or None,
        "property_name": (request.args.get("property_name") or "").strip() or None,
        "date_from": _parse_date(request.args.get("from")),
        "date_to": _parse_date(request.args.get("to")),
    }


@cleaning_bp.get("/partners")
@require_auth
@require_account
def partners_list() -> tuple[Any, int]:
    gate = _gate()
    if gate is not None:
        return gate
    return jsonify(list_partners(g.ctx, _account_id()).model_dump()), 200


@cleaning_bp.post("/partners")
@require_auth
@require_account
def partners_create() -> tuple[Any, int]:
    gate = _gate()
    if gate is not None:
        return gate
    body = PartnerCreateRequest.model_validate(request.get_json(silent=True) or {})
    created = create_partner(g.ctx, _account_id(), body)
    return jsonify(created.model_dump()), 201


@cleaning_bp.put("/partners/<partner_id>")
@require_auth
@require_account
def partners_update(partner_id: str) -> tuple[Any, int]:
    gate = _gate()
    if gate is not None:
        return gate
    body = PartnerUpdateRequest.model_validate(request.get_json(silent=True) or {})
    updated = update_partner(g.ctx, _account_id(), partner_id, body)
    if updated is None:
        return jsonify({"error": "Partner nicht gefunden", "code": 404}), 404
    return jsonify(updated.model_dump()), 200


@cleaning_bp.delete("/partners/<partner_id>")
@require_auth
@require_account
def partners_delete(partner_id: str) -> tuple[Any, int]:
    gate = _gate()
    if gate is not None:
        return gate
    if not deactivate_partner(g.ctx, _account_id(), partner_id):
        return jsonify({"error": "Partner nicht gefunden", "code": 404}), 404
    return jsonify({"ok": True}), 200


@cleaning_bp.get("/tasks")
@require_auth
@require_account
def tasks_list() -> tuple[Any, int]:
    gate = _gate()
    if gate is not None:
        return gate
    result = list_tasks(g.ctx, _account_id(), **_filters())
    return jsonify(result.model_dump()), 200


@cleaning_bp.patch("/tasks/<task_id>")
@require_auth
@require_account
def tasks_update(task_id: str) -> tuple[Any, int]:
    gate = _gate()
    if gate is not None:
        return gate
    body = TaskUpdateRequest.model_validate(request.get_json(silent=True) or {})
    updated = update_task(g.ctx, _account_id(), task_id, body)
    if updated is None:
        return jsonify({"error": "Auftrag nicht gefunden", "code": 404}), 404
    return jsonify(updated.model_dump()), 200


@cleaning_bp.get("/tasks/export")
@require_auth
@require_account
def tasks_export() -> Response | tuple[Any, int]:
    gate = _gate()
    if gate is not None:
        return gate
    data = export_tasks_xlsx(g.ctx, _account_id(), **_filters())
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    return Response(
        data,
        mimetype=_XLSX_MIME,
        headers={
            "Content-Disposition": f'attachment; filename="Putzplan_{stamp}.xlsx"'
        },
    )
