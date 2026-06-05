"""Auth-Endpoints."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError
from werkzeug.security import check_password_hash, generate_password_hash

from backend.api.auth.account_access import account_login_error, load_user_account
from backend.api.auth.models import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from backend.api.auth.token_blocklist import _exp_from_payload, is_revoked, revoke
from backend.api.auth.tokens import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.api.middleware.auth_guard import require_auth

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _user_response(user: object) -> UserResponse:
    from backend.infrastructure.repositories.user_repository import UserRecord

    assert isinstance(user, UserRecord)
    account = load_user_account(user, g.ctx.account_repo)
    mail_status: str | None = None
    mail_onboarding_done: bool | None = None
    if user.role == "platform_admin":
        mail_onboarding_done = True
    elif user.account_id:
        mail_conn = g.ctx.mail_connection_repo.get(user.account_id)
        if mail_conn is not None:
            mail_status = mail_conn.status
            mail_onboarding_done = mail_conn.onboarding_completed
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        account_id=user.account_id,
        first_name=user.first_name,
        last_name=user.last_name,
        account_status=account.status if account else None,
        account_display_name=account.display_name if account else None,
        mail_connection_status=mail_status,
        mail_onboarding_completed=mail_onboarding_done,
    )


def _login_blocked(user: object) -> tuple[Any, int] | None:
    from backend.infrastructure.repositories.user_repository import UserRecord

    assert isinstance(user, UserRecord)
    account = load_user_account(user, g.ctx.account_repo)
    error = account_login_error(account)
    if error is None:
        return None
    return (
        jsonify(
            {
                "error": error,
                "code": 403,
                "account_status": account.status if account else None,
            }
        ),
        403,
    )


@auth_bp.post("/register")
def register() -> tuple[Any, int]:
    """Registrierung – Account startet im Status pending (Freischaltung nötig)."""
    try:
        body = RegisterRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": exc.errors()[0]["msg"], "code": 400}), 400

    email = str(body.email).lower()
    if g.ctx.user_repo.get_by_email(email) is not None:
        return jsonify({"error": "E-Mail ist bereits registriert", "code": 409}), 409

    display_name = (
        body.company_name.strip()
        if body.account_type == "business" and body.company_name
        else f"{body.first_name.strip()} {body.last_name.strip()}"
    )
    account = g.ctx.account_repo.create(
        display_name=display_name,
        contact_email=email,
        account_type=body.account_type,
        company_name=body.company_name,
        phone=body.phone,
        status="pending",
    )
    # mail_ingest_anchor_at = created_at — begrenzt Erst-Import (Roadmap Phase 7)
    assert account.mail_ingest_anchor_at is not None
    g.ctx.user_repo.create(
        email,
        generate_password_hash(body.password),
        account_id=account.id,
        role="owner",
        first_name=body.first_name,
        last_name=body.last_name,
        phone=body.phone,
    )
    return (
        jsonify(
            RegisterResponse(
                message=(
                    "Registrierung eingegangen. Dein Konto wird geprüft – "
                    "du kannst dich anmelden, sobald es freigeschaltet wurde."
                ),
                account_id=account.id,
                status=account.status,
            ).model_dump()
        ),
        201,
    )


@auth_bp.post("/login")
def login() -> tuple[Any, int]:
    """Login mit E-Mail und Passwort."""
    body = LoginRequest.model_validate(request.get_json(silent=True) or {})
    user = g.ctx.user_repo.get_by_email(str(body.email))
    if user is None or not check_password_hash(user.password_hash, body.password):
        return jsonify({"error": "Invalid credentials", "code": 401}), 401
    blocked = _login_blocked(user)
    if blocked is not None:
        return blocked
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
            revoke(jti, expires_at=_exp_from_payload(payload.get("exp")))
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
    return jsonify(_user_response(user).model_dump()), 200


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
    blocked = _login_blocked(user)
    if blocked is not None:
        return blocked
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
