"""CLI: ein Lauf der Putz-Erinnerungen (Vortags-WhatsApp) über alle Mandanten."""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from backend.core.config.factory import build_app_context
    from backend.core.config.settings import get_settings
    from backend.features.cleaning.reminder_service import (
        build_cleaning_reminder_service,
    )
except ModuleNotFoundError as exc:
    print(
        "Import fehlgeschlagen (venv / Pakete fehlen). "
        'Aktiviere .venv und `pip install -e ".[dev]"`. '
        f"Details: {exc}",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    """Run the command workflow."""
    settings = get_settings()
    ctx = build_app_context(settings)
    service = build_cleaning_reminder_service(ctx)
    if service is None:
        logger.warning("Cleaning reminder service not wired — nothing to do.")
        return 0
    now = datetime.now(UTC)
    sent = service.run_all(today=now.date(), now_hour=now.hour)
    logger.info("Cleaning reminders sent: %s", sent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
