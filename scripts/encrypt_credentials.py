"""Verschlüsselt vorhandene Klartext-Credentials in MongoDB nach.

Voraussetzung: CREDENTIALS_ENCRYPTION_KEY ist in der .env gesetzt.
Idempotent — bereits verschlüsselte Werte bleiben unverändert.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    """Liest alle Records und speichert sie neu (save() verschlüsselt)."""
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from backend.core.config.settings import get_settings
    from backend.core.utils.field_crypto import FieldCipher
    from backend.infrastructure.repositories.mail_connection_repository import (
        MailConnectionRepository,
    )
    from backend.infrastructure.repositories.mongo import get_database
    from backend.infrastructure.repositories.platform_settings_repository import (
        PlatformSettingsRepository,
    )

    settings = get_settings()
    cipher = FieldCipher(settings.credentials_encryption_key)
    if not cipher.enabled:
        print("CREDENTIALS_ENCRYPTION_KEY nicht gesetzt — nichts zu tun.")
        return 1

    db = get_database(settings)
    mail_repo = MailConnectionRepository(db, cipher)
    settings_repo = PlatformSettingsRepository(db, cipher)

    mail_count = 0
    for record in mail_repo.list_all():
        mail_repo.save(record)
        mail_count += 1

    settings_count = 0
    for doc in db[PlatformSettingsRepository.COLLECTION].find({}, {"_id": 1}):
        account_id = str(doc["_id"])
        settings_record = settings_repo.get(account_id)
        if settings_record is not None:
            settings_record.id = account_id
            settings_repo.save(settings_record)
            settings_count += 1

    print(f"Verschlüsselt: {mail_count} Mail-Verbindungen, {settings_count} Settings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
