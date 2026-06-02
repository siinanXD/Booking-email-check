"""Setzt Intent auf other für erkannte Marketing-/Newsletter-Mails."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _bootstrap import require_project_venv, safe_print

require_project_venv()


def main() -> int:
    from config.factory import build_app_context
    from config.settings import get_settings
    from models.email import StoredEmail
    from schemas.booking.taxonomy import BookingIntent
    from services.booking_relevance import is_marketing_noise

    ctx = build_app_context(get_settings())
    fixed = 0
    for doc in ctx.email_repo._col.find():
        email = StoredEmail.from_mongo(doc)
        if not is_marketing_noise(email):
            continue
        ext = ctx.extraction_repo.get_by_correlation_id(email.correlation_id)
        if ext is None or ext.intent == BookingIntent.OTHER:
            continue
        ext.intent = BookingIntent.OTHER
        ext.booking_number = None
        ext.platform = None
        ctx.extraction_repo.save(
            email.correlation_id,
            email.message_id,
            ext,
        )
        safe_print(f"-> other: {(email.subject or '')[:50]}")
        fixed += 1
    safe_print(f"{fixed} Extraktionen auf other gesetzt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
