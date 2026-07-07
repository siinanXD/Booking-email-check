"""CLI: Backfill legacy subscriptions for active accounts."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    """Idempotent: active → legacy, andere ohne Abo werden übersprungen."""
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from backend.core.config.settings import get_settings
    from backend.features.billing.backfill import run_backfill
    from backend.infrastructure.repositories.mongo import get_database

    settings = get_settings()
    created, skipped = run_backfill(get_database(settings))
    print(
        f"Fertig: {created} legacy angelegt, "
        f"{skipped} übersprungen (bereits Abo oder nicht active)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
