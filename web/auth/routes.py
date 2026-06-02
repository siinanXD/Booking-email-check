"""Auth-Endpoints."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, g, jsonify, request
from werkzeug.security import check_password_hash

from web.auth.models import LoginRequest, TokenResponse, UserResponse
from web.auth.token_blocklist import is_revoked, revoke
from web.auth.tokens import create_access_token, create_refresh_token, decode_token
from web.middleware.auth_guard import require_auth

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/login")
def login() -> tuple[Any, int]:
    """Login mit E-Mail und Passwort."""
    body = LoginRequest.model_validate(request.get_json(silent=True) or {})
    user = g.ctx.user_repo.get_by_email(str(body.email))
    if user is None or not check_password_hash(user.password_hash, body.password):
        return jsonify({"error": "Invalid credentials", "code": 401}), 401
    access = create_access_token(user, g.settings)
    refresh = create_refresh_token(user, g.settings)
    return (
        jsonify(TokenResponse(access_token=access, refresh_token=refresh).model_dump()),
        200,
    )


@auth_bp.post("/logout")
@require_auth
def logout() -> tuple[Any, int]:
    """Widerruft das aktuelle Access-Token (jti)."""
    header = request.headers.get("Authorization", "")
    token = header[7:].strip() if header.startswith("Bearer ") else ""
    try:
        payload = decode_token(token, g.settings)
        jti = payload.get("jti")
        if isinstance(jti, str):
            revoke(jti)
    except Exception:
        pass
    return jsonify({"status": "logged_out"}), 200


@auth_bp.get("/me")
@require_auth
def me() -> tuple[Any, int]:
    """Aktueller Benutzer."""
    user = g.ctx.user_repo.get_by_id(str(g.current_user["id"]))
    if user is None:
        return jsonify({"error": "User not found", "code": 404}), 404
    return (
        jsonify(
            UserResponse(id=user.id, email=user.email, role=user.role).model_dump()
        ),
        200,
    )


@auth_bp.post("/refresh")
def refresh() -> tuple[Any, int]:
    """Neues Access-Token aus Refresh-Token."""
    data = request.get_json(silent=True) or {}
    refresh_token = data.get("refresh_token")
    if not isinstance(refresh_token, str):
        return jsonify({"error": "refresh_token required", "code": 400}), 400
    try:
        payload = decode_token(refresh_token, g.settings)
    except Exception:
        return jsonify({"error": "Invalid refresh token", "code": 401}), 401
    if payload.get("type") != "refresh":
        return jsonify({"error": "Invalid token type", "code": 401}), 401
    jti = payload.get("jti")
    if isinstance(jti, str) and is_revoked(jti):
        return jsonify({"error": "Token revoked", "code": 401}), 401
    user = g.ctx.user_repo.get_by_id(str(payload.get("sub")))
    if user is None:
        return jsonify({"error": "User not found", "code": 404}), 404
    access = create_access_token(user, g.settings)
    return (
        jsonify(
            TokenResponse(
                access_token=access,
                refresh_token=refresh_token,
            ).model_dump()
        ),
        200,
    )
