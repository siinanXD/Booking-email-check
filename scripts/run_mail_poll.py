"""CLI: ein Poll-Lauf über alle aktiven Mandanten mit Postfach-Konfiguration."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_VENV_PY = _ROOT / ".venv" / "Scripts" / "python.exe"


def _venv_hint() -> None:
    if not _VENV_PY.exists():
        return
    try:
        if Path(sys.executable).resolve() != _VENV_PY.resolve():
            print(
                "Hinweis: .venv nicht aktiv. Nutze:\n"
                "  .\\.venv\\Scripts\\Activate.ps1\n"
                "  python scripts/run_mail_poll.py\n"
                "Oder: .\\scripts\\run_mail_poll.ps1",
                file=sys.stderr,
            )
    except OSError:
        return


def _import_error_help(exc: ModuleNotFoundError) -> None:
    print(
        "Import fehlgeschlagen (venv / Pakete fehlen):\n"
        "  py -3.11 -m venv .venv\n"
        "  .\\.venv\\Scripts\\Activate.ps1\n"
        '  pip install -e ".[dev]"\n'
        f"Details: {exc}",
        file=sys.stderr,
    )


_venv_hint()

try:
    from backend.core.config.factory import build_app_context
    from backend.core.config.settings import get_settings
    from backend.features.mail.mail_poll_service import (
        build_mail_poll_service_from_context,
    )
except ModuleNotFoundError as exc:
    _import_error_help(exc)
    raise SystemExit(1) from exc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_poll() -> int:
    """Führt einen Poll-Lauf aus."""
    settings = get_settings()
    mode = settings.llm_mode.strip().lower()
    logger.info(
        "Mail poll: LLM_MODE=%s, fetch_max=%s, unread_only=%s",
        mode,
        settings.outlook_fetch_max,
        settings.outlook_fetch_unread_only,
    )
    ctx = build_app_context(settings)
    service = build_mail_poll_service_from_context(ctx, settings)
    result = service.run_all(max_workers=settings.mail_poll_max_workers)
    for summary in result.summaries:
        if summary.fetch_error:
            logger.error(
                "account=%s provider=%s fetch_error=%s",
                summary.account_id,
                summary.provider,
                summary.fetch_error,
            )
        elif summary.item_errors:
            logger.warning(
                "account=%s provider=%s processed=%s item_errors=%s",
                summary.account_id,
                summary.provider,
                summary.processed,
                len(summary.item_errors),
            )
        else:
            logger.info(
                "account=%s provider=%s processed=%s duplicates=%s",
                summary.account_id,
                summary.provider,
                summary.processed,
                summary.duplicates,
            )
    logger.info(
        "Poll done: accounts=%s new_ingests=%s",
        result.accounts_polled,
        result.total_processed,
    )
    return 0


def main() -> int:
    """Run the command workflow."""
    return run_poll()


if __name__ == "__main__":
    sys.exit(main())
