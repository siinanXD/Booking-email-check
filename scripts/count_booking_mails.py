"""Zählt echte Buchungs-Mails vs. Gesamtbestand."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _bootstrap import require_project_venv, safe_print

require_project_venv()

from datetime import UTC, datetime, timedelta

from config.factory import build_app_context
from config.settings import get_settings
from services.booking_relevance import count_booking_mails


def main() -> int:
    ctx = build_app_context(get_settings())
    week_iso = (
        (datetime.now(UTC) - timedelta(days=7))
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .isoformat()
    )
    total, booking, by_intent = count_booking_mails(
        ctx.email_repo,
        ctx.extraction_repo,
    )
    _, booking_week, by_week = count_booking_mails(
        ctx.email_repo,
        ctx.extraction_repo,
        since_iso=week_iso,
    )
    pending_all = ctx.review_repo.count_pending()
    pending_booking = len(
        __import__("web.services.query_service", fromlist=["QueryService"])
        .QueryService(ctx)
        .list_review_pending(limit=500)
    )

    safe_print("=== Buchungs-Mail-Zaehlung ===")
    safe_print(f"E-Mails gesamt (DB):     {total}")
    safe_print(f"Buchungs-Mails gesamt:   {booking}")
    safe_print(f"Buchungs-Mails (7 Tage): {booking_week}")
    safe_print(f"Review pending (alle):   {pending_all}")
    safe_print(f"Review pending (Buchung): {pending_booking}")
    if by_intent:
        safe_print("Nach Intent (Buchung):")
        for k, v in sorted(by_intent.items(), key=lambda x: -x[1]):
            safe_print(f"  {k}: {v}")
    if by_week:
        safe_print("Letzte 7 Tage (Buchung):")
        for k, v in sorted(by_week.items(), key=lambda x: -x[1]):
            safe_print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
