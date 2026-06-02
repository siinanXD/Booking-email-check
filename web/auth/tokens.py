"""JWT-Hilfsfunktionen."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from config.settings import Settings
from repositories.user_repository import UserRecord


def _now() -> datetime:
    return datetime.now(UTC)


def create_access_token(user: UserRecord, settings: Settings) -> str:
    """Erzeugt Access-JWT."""
    return _encode(
        {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "type": "access",
            "jti": uuid.uuid4().hex,
        },
        settings,
        expires_seconds=settings.jwt_access_expires,
    )


def create_refresh_token(user: UserRecord, settings: Settings) -> str:
    """Erzeugt Refresh-JWT."""
    return _encode(
        {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "type": "refresh",
            "jti": uuid.uuid4().hex,
        },
        settings,
        expires_seconds=settings.jwt_refresh_expires,
    )


def decode_token(token: str, settings: Settings) -> dict[str, Any]:
    """Dekodiert und validiert JWT."""
    secret = settings.flask_secret_key
    if not secret:
        msg = "FLASK_SECRET_KEY is not configured"
        raise ValueError(msg)
    payload: dict[str, Any] = jwt.decode(token, secret, algorithms=["HS256"])
    return payload


def _encode(
    payload: dict[str, Any],
    settings: Settings,
    *,
    expires_seconds: int,
) -> str:
    secret = settings.flask_secret_key
    if not secret:
        msg = "FLASK_SECRET_KEY is not configured"
        raise ValueError(msg)
    data = {
        **payload,
        "exp": _now() + timedelta(seconds=expires_seconds),
        "iat": _now(),
    }
    encoded = jwt.encode(data, secret, algorithm="HS256")
    return str(encoded)
