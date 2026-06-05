"""Einmalige Migration: mail_ingest_anchor_at + mail_initial_sync_completed_at."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from backend.core.config.factory import build_app_context


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill mail ingest flags for accounts"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur anzeigen, keine Schreiboperationen",
    )
    args = parser.parse_args()
    ctx = build_app_context()
    col = ctx.account_repo._col
    now = datetime.now(UTC)
    updated = 0
    for doc in col.find({}):
        account_id = doc["_id"]
        changes: dict[str, object] = {}
        if not doc.get("mail_ingest_anchor_at"):
            anchor = doc.get("created_at") or now.isoformat()
            changes["mail_ingest_anchor_at"] = anchor
        if doc.get("mail_ingest_lookback_count") is None:
            changes["mail_ingest_lookback_count"] = 50
        if doc.get("mail_initial_sync_completed_at") is None:
            changes["mail_initial_sync_completed_at"] = now.isoformat()
        if not changes:
            continue
        changes["updated_at"] = now.isoformat()
        updated += 1
        print(f"  {account_id}: {list(changes.keys())}")
        if not args.dry_run:
            col.update_one({"_id": account_id}, {"$set": changes})
    print(f"Done — {updated} account(s) {'would be ' if args.dry_run else ''}updated.")


if __name__ == "__main__":
    main()
