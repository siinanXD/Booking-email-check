"""Backfill: is_booking + effective_intent auf bestehenden Mails neu berechnen.

Quelle der Wahrheit ist ``relevance_fields`` aus booking_relevance.py — dieselbe
Funktion, die der Workflow beim Extrahieren nutzt. Nach Änderungen an der
Klassifikationslogik dieses Skript erneut laufen lassen.

Idempotent (schreibt nur bei Änderung), mandantensicher (pro Dokument), mit
``--dry-run`` (Vorschau) und ``--account-id`` (auf einen Mandanten begrenzen).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _bootstrap import require_project_venv, safe_print

require_project_venv()


def main() -> int:
    """Recompute is_booking/effective_intent für alle Emails."""
    from backend.ai.domain.booking.booking_relevance import relevance_fields
    from backend.core.config.factory import build_app_context
    from backend.core.config.settings import get_settings
    from backend.core.models.email import StoredEmail

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Nur anzeigen")
    parser.add_argument("--account-id", default=None, help="Nur ein Mandant")
    args = parser.parse_args()

    ctx = build_app_context(get_settings())
    query: dict[str, str] = {}
    if args.account_id:
        query["account_id"] = args.account_id

    scanned = 0
    updated = 0
    for doc in ctx.email_repo._col.find(query):
        scanned += 1
        email = StoredEmail.from_mongo(doc)
        ext = ctx.extraction_repo.get_by_correlation_id(
            email.correlation_id,
            account_id=email.account_id,
        )
        fields = relevance_fields(email, ext)
        if (
            doc.get("is_booking") == fields["is_booking"]
            and doc.get("effective_intent") == fields["effective_intent"]
        ):
            continue
        updated += 1
        safe_print(
            f"-> {email.correlation_id}: is_booking={fields['is_booking']} "
            f"intent={fields['effective_intent']} | {(email.subject or '')[:40]}"
        )
        if not args.dry_run:
            ctx.email_repo._col.update_one(
                {"_id": doc["_id"]},
                {"$set": fields},
            )

    verb = "würden aktualisiert" if args.dry_run else "aktualisiert"
    safe_print(f"Fertig — {scanned} gescannt, {updated} {verb}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
