"""Legt den Admin-Benutzer aus ENV an (idempotent)."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    """Seed Admin-User."""
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from werkzeug.security import generate_password_hash

    from config.settings import get_settings
    from repositories.mongo import get_database
    from repositories.user_repository import UserRepository

    settings = get_settings()
    if not settings.admin_password:
        print("ADMIN_PASSWORD nicht gesetzt – Seed übersprungen.")
        return 0
    if not settings.flask_secret_key:
        print("WARNUNG: FLASK_SECRET_KEY nicht gesetzt.")
    db = get_database(settings)
    users = UserRepository(db)
    users.ensure_admin(
        settings.admin_email,
        generate_password_hash(settings.admin_password),
    )
    print(f"Admin bereit: {settings.admin_email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
