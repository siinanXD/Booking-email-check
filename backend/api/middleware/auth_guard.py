"""JWT-Schutz für API-Routes."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from flask import g, jsonify, request

from backend.api.auth.token_blocklist import is_revoked
from backend.api.auth.tokens import decode_token
from backend.core.config.settings import Settings
from backend.features.billing.access import account_api_access_error

F = TypeVar("F", bound=Callable[..., Any])


def require_auth(fn: F) -> F:
    """Decorator: Bearer-JWT erforderlich."""

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Validiert Bearer-JWT und setzt g.current_user."""
        settings: Settings = g.settings
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized", "code": 401}), 401
        token = header[7:].strip()
        try:
            payload = decode_token(token, settings)
        except Exception:
            return jsonify({"error": "Invalid token", "code": 401}), 401
        if payload.get("type") != "access":
            return jsonify({"error": "Invalid token type", "code": 401}), 401
        jti = payload.get("jti")
        if isinstance(jti, str) and is_revoked(jti):
            return jsonify({"error": "Token revoked", "code": 401}), 401

        user_id = payload.get("sub")
        account_id = payload.get("account_id")
        role = payload.get("role")

        # Check user lock + account expiry (skip for platform_admin)
        if role != "platform_admin" and isinstance(user_id, str):
            user = g.ctx.user_repo.get_by_id(user_id)
            if user is None:
                return jsonify({"error": "Unauthorized", "code": 401}), 401
            if user.is_locked:
                return jsonify({"error": "Account gesperrt", "code": 403}), 403
            if isinstance(account_id, str):
                account = g.ctx.account_repo.get_by_id(account_id)
                subscription = g.ctx.subscription_repo.get_by_account(account_id)
                access_error = account_api_access_error(account, subscription)
                if access_error is not None:
                    return jsonify({"error": access_error, "code": 403}), 403

        g.current_user = {
            "id": user_id,
            "email": payload.get("email"),
            "role": role,
            "account_id": account_id if isinstance(account_id, str) else None,
        }
        g.current_account_id = account_id if isinstance(account_id, str) else None
        return fn(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
