"""Legt den Plattform-Admin aus ENV an (idempotent)."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    """Seed Plattform-Admin mit aktivem Account."""
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from werkzeug.security import check_password_hash, generate_password_hash

    from backend.core.config.settings import get_settings
    from backend.core.utils.field_crypto import FieldCipher
    from backend.infrastructure.repositories.account_repository import AccountRepository
    from backend.infrastructure.repositories.mail_connection_repository import (
        MailConnectionRepository,
    )
    from backend.infrastructure.repositories.mongo import get_database
    from backend.infrastructure.repositories.user_repository import UserRepository

    settings = get_settings()
    if not settings.admin_password:
        print("ADMIN_PASSWORD nicht gesetzt – Seed übersprungen.")
        return 0
    if not settings.flask_secret_key:
        print("WARNUNG: FLASK_SECRET_KEY nicht gesetzt.")
    db = get_database(settings)
    accounts = AccountRepository(db)
    users = UserRepository(db)
    mail_connections = MailConnectionRepository(
        db, FieldCipher(settings.credentials_encryption_key)
    )

    def _skip_mail_onboarding(account_id: str) -> None:
        record = mail_connections.get_or_create(account_id)
        if not record.onboarding_completed:
            record.onboarding_completed = True
            mail_connections.save(record)
            print(f"Mail-Onboarding übersprungen für Account {account_id}")

    pw_hash = generate_password_hash(settings.admin_password)
    existing = users.get_by_email(settings.admin_email)
    if existing is not None:
        updates: dict[str, object] = {}
        if existing.role != "platform_admin":
            updates["role"] = "platform_admin"
        if not check_password_hash(existing.password_hash, settings.admin_password):
            updates["password_hash"] = pw_hash
        if updates:
            db[UserRepository.COLLECTION].update_one(
                {"_id": existing.id},
                {"$set": updates},
            )
            if "role" in updates:
                print(f"Rolle aktualisiert: {settings.admin_email} → platform_admin")
            if "password_hash" in updates:
                print(f"Passwort aus .env übernommen: {settings.admin_email}")
        else:
            print(f"Plattform-Admin bereit: {settings.admin_email}")
        if not existing.account_id:
            account = accounts.create(
                display_name="Plattform-Administration",
                contact_email=settings.admin_email,
                account_type="business",
                company_name="Plattform-Administration",
                status="active",
            )
            db[UserRepository.COLLECTION].update_one(
                {"_id": existing.id},
                {"$set": {"account_id": account.id}},
            )
            _skip_mail_onboarding(account.id)
        elif existing.account_id:
            _skip_mail_onboarding(existing.account_id)
        return 0

    account = accounts.create(
        display_name="Plattform-Administration",
        contact_email=settings.admin_email,
        account_type="business",
        company_name="Plattform-Administration",
        status="active",
    )
    users.ensure_platform_admin(
        settings.admin_email,
        generate_password_hash(settings.admin_password),
        account_id=account.id,
    )
    _skip_mail_onboarding(account.id)
    print(f"Plattform-Admin bereit: {settings.admin_email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
