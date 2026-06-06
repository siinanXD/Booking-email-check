"""Löscht gespeicherte WhatsApp-Credentials aus platform_settings in MongoDB.

Nach diesem Script nutzt merge_platform_settings immer den Railway-Env-Token.
Starte mit: python scripts/reset_whatsapp_token_from_db.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.config.settings import get_settings
from backend.infrastructure.repositories.mongo import get_database

settings = get_settings()
db = get_database(settings)
col = db["platform_settings"]

docs = list(col.find({}))
if not docs:
    print("Keine platform_settings-Dokumente gefunden.")
    sys.exit(0)

for doc in docs:
    account_id = doc.get("_id", "?")
    token = str(doc.get("whatsapp_access_token") or "").strip()
    phone_id = str(doc.get("whatsapp_phone_number_id") or "").strip()

    if not token and not phone_id:
        print(f"  {account_id}: bereits leer, nichts zu tun")
        continue

    col.update_one(
        {"_id": account_id},
        {"$set": {"whatsapp_access_token": "", "whatsapp_phone_number_id": ""}},
    )
    print(f"  {account_id}: token und phone_number_id geleert")

print("\nFertig — ab jetzt wird der Railway-Env-Token verwendet.")
