"""Erzeugt Review-Entwürfe für bereits verarbeitete Mails ohne pending Review."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _bootstrap import require_project_venv, safe_print

require_project_venv()

from models.email import ProcessingState
from schemas.booking.taxonomy import BookingIntent
from services.booking_relevance import is_booking_relevant


def main() -> int:
    from config.factory import build_app_context
    from config.settings import get_settings

    ctx = build_app_context(get_settings())
    wf = ctx.workflow
    limit = 25
    created = 0
    skipped = 0

    states = {
        ProcessingState.VALIDATED.value,
        ProcessingState.RETRIEVED.value,
        ProcessingState.EXTRACTED.value,
        ProcessingState.DRAFTED.value,
    }
    cursor = ctx.email_repo._col.find({"processing_state": {"$in": list(states)}}).sort(
        "updated_at", -1
    )

    for doc in cursor:
        if created >= limit:
            break
        email = ctx.email_repo.get_by_message_id(doc.get("message_id") or doc["_id"])
        if email is None:
            continue
        if ctx.review_repo.get(email.correlation_id) is not None:
            skipped += 1
            continue
        ext = ctx.extraction_repo.get_by_correlation_id(email.correlation_id)
        if not is_booking_relevant(email, ext):
            skipped += 1
            continue
        if ext and ext.intent == BookingIntent.OTHER:
            skipped += 1
            continue
        try:
            wf.run(email, thread_id=email.correlation_id)
            created += 1
            safe_print(f"Review-Entwurf: {(email.subject or '')[:50]}")
        except Exception as exc:
            print(f"Fehler {email.correlation_id}: {exc}", file=sys.stderr)

    safe_print(f"Fertig: {created} erstellt, {skipped} uebersprungen (Limit {limit}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
