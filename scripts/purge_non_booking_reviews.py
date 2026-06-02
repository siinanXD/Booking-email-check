"""Entfernt Review-Eintraege ohne echte Buchungs-Mail."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _bootstrap import require_project_venv, safe_print

require_project_venv()

from config.factory import build_app_context
from config.settings import get_settings
from models.email import StoredEmail
from services.booking_relevance import classify_booking_mail


def main() -> int:
    ctx = build_app_context(get_settings())
    removed = 0
    kept = 0
    for doc in ctx.review_repo._col.find({"review_status": "pending"}):
        cid = doc.get("_id") or doc.get("correlation_id")
        email_doc = ctx.email_repo._col.find_one({"correlation_id": cid})
        if email_doc is None:
            ctx.review_repo._col.delete_one({"_id": cid})
            removed += 1
            continue
        email = StoredEmail.from_mongo(email_doc)
        ext = ctx.extraction_repo.get_by_correlation_id(str(cid))
        if classify_booking_mail(email, ext).is_booking:
            kept += 1
            safe_print(f"behalten: {(email.subject or '')[:50]}")
        else:
            ctx.review_repo._col.delete_one({"_id": cid})
            removed += 1
            safe_print(f"entfernt: {(email.subject or '')[:50]}")
    safe_print(f"Fertig: {kept} behalten, {removed} entfernt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
