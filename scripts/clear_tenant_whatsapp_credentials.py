"""Einmalige Migration: entfernt per-Tenant WhatsApp-Credentials aus platform_settings.

Hintergrund: platform_from_env hat bisher access_token und phone_number_id in das
DB-Dokument jedes Tenants kopiert. Dadurch wurden Env-Aktualisierungen nicht mehr
übernommen (merge_platform_settings bevorzugt nicht-leere DB-Werte).

Nach diesem Skript gilt: Tenants ohne eigene Credentials erben immer den aktuellen
Env-Wert. Tenants mit bewusst eingetragenen Credentials (anderer Wert als Env) bleiben
unberührt.
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

env_token = settings.whatsapp_access_token.strip()
env_phone_id = settings.whatsapp_phone_number_id.strip()

docs = list(col.find({}))
cleared = 0

for doc in docs:
    account_id = doc.get("_id", "?")
    token = (doc.get("whatsapp_access_token") or "").strip()
    phone_id = (doc.get("whatsapp_phone_number_id") or "").strip()

    updates: dict[str, str] = {}
    if token and token == env_token:
        updates["whatsapp_access_token"] = ""
    if phone_id and phone_id == env_phone_id:
        updates["whatsapp_phone_number_id"] = ""

    if updates:
        col.update_one({"_id": account_id}, {"$set": updates})
        print(f"  {account_id}: cleared {list(updates.keys())}")
        cleared += 1
    else:
        print(f"  {account_id}: skipped (no env-copy detected or own credentials)")

print(f"\nDone — {cleared}/{len(docs)} tenant records updated.")
