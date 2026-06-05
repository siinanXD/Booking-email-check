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
    ctx: object,
    correlation_id: str,
    account_id: str | None,
    body: str,
    extraction: object | None,
) -> None:
    indexing = getattr(ctx, "indexing_service", None)
    if indexing is None:
        return
    await indexing._index_async(
        correlation_id,
        body,
        extraction,
        account_id,
    )


def main() -> int:
    """Re-Indexiert Bestands-Mails mit semantischem Chunking."""
    from backend.ai.domain.booking.extraction import parse_stored_extraction
    from backend.core.config.factory import build_app_context
    from backend.core.config.settings import get_settings
    from backend.core.models.email import ProcessingState

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

    for doc in cursor:
        if args.limit and processed >= args.limit:
            break
        correlation_id = doc.get("correlation_id") or doc.get("_id")
        account_id = doc.get("account_id")
        body = (doc.get("body_text") or "").strip()
        if not body:
            skipped += 1
            continue
        if args.dry_run:
            processed += 1
            safe_print(f"[dry-run] {correlation_id}")
            continue
        extraction = parse_stored_extraction(
            ctx.extraction_repo.get_by_correlation_id(
                correlation_id,
                account_id=account_id,
            )
        )
        asyncio.run(
            _reindex_one(
                ctx,
                correlation_id,
                account_id,
                body,
                extraction,
            )
        )
        processed += 1
        safe_print(f"Re-indexiert: {correlation_id}")

    safe_print(f"Fertig: {processed} indexiert, {skipped} übersprungen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
