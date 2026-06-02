"""JWT-Schutz für API-Routes."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from flask import g, jsonify, request

from config.settings import Settings
from web.auth.token_blocklist import is_revoked
from web.auth.tokens import decode_token

F = TypeVar("F", bound=Callable[..., Any])


def require_auth(fn: F) -> F:
    """Decorator: Bearer-JWT erforderlich."""

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
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
        g.current_user = {
            "id": payload.get("sub"),
            "email": payload.get("email"),
            "role": payload.get("role"),
        }
        return fn(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
