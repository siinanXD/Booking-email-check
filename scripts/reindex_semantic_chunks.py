"""Re-Indexiert Mails mit semantischem Chunking (einmalig nach Deploy Phase 12)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _bootstrap import require_project_venv, safe_print

require_project_venv()

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.core.config.factory import AppContext


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-Indexiert Embeddings/Chunks mit semantic_chunk().",
    )
    parser.add_argument(
        "--account-id",
        help="Nur Mails dieses Mandanten (account_id UUID).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max. Anzahl Mails (0 = unbegrenzt).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur zählen, keine Indexierung.",
    )
    return parser.parse_args()


async def _reindex_one(
    ctx: AppContext,
    correlation_id: str,
    account_id: str | None,
    body: str,
    extraction: BookingExtraction | None,
) -> None:
    if ctx.indexing_service is None:
        return
    await ctx.indexing_service._index_async(
        correlation_id,
        body,
        extraction,
        account_id,
    )


def main() -> int:
    """Re-Indexiert Bestands-Mails mit semantischem Chunking."""
    from backend.ai.domain.booking.booking_relevance import is_booking_relevant
    from backend.ai.domain.booking.extraction import parse_stored_extraction
    from backend.core.config.factory import build_app_context
    from backend.core.config.settings import get_settings
    from backend.core.models.email import ProcessingState, StoredEmail

    args = _parse_args()
    ctx = build_app_context(get_settings())
    if ctx.indexing_service is None:
        print("IndexingService nicht konfiguriert.", file=sys.stderr)
        return 1

    states = {
        ProcessingState.VALIDATED.value,
        ProcessingState.RETRIEVED.value,
        ProcessingState.EXTRACTED.value,
        ProcessingState.DRAFTED.value,
    }
    query: dict[str, object] = {"processing_state": {"$in": list(states)}}
    if args.account_id:
        query["account_id"] = args.account_id

    cursor = ctx.email_repo._col.find(query).sort("updated_at", -1)
    processed = 0
    skipped = 0
    purged = 0

    for doc in cursor:
        if args.limit and processed >= args.limit:
            break
        raw_cid = doc.get("correlation_id") or doc.get("_id")
        if not isinstance(raw_cid, str) or not raw_cid:
            skipped += 1
            continue
        correlation_id = raw_cid
        account_raw = doc.get("account_id")
        account_id: str | None = account_raw if isinstance(account_raw, str) else None
        body = (doc.get("body_text") or "").strip()
        if not body:
            skipped += 1
            continue
        extraction = parse_stored_extraction(
            ctx.extraction_repo.get_by_correlation_id(
                correlation_id,
                account_id=account_id,
            )
        )
        # Nur buchungsrelevante Mails gehören in den Vektor-Index; Nicht-Buchung
        # (intent=other, Marketing) wird stattdessen aus dem Index entfernt.
        relevant = is_booking_relevant(StoredEmail.from_mongo(doc), extraction)
        if args.dry_run:
            processed += 1
            safe_print(f"[dry-run] {'index' if relevant else 'purge'} {correlation_id}")
            continue
        if not relevant:
            ctx.indexing_service.purge(correlation_id, account_id=account_id)
            purged += 1
            safe_print(f"Gepurged (Nicht-Buchung): {correlation_id}")
            continue
        asyncio.run(_reindex_one(ctx, correlation_id, account_id, body, extraction))
        processed += 1
        safe_print(f"Re-indexiert: {correlation_id}")

    safe_print(
        f"Fertig: {processed} indexiert, {purged} gepurged, {skipped} übersprungen."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
