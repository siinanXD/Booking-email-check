"""CLI: Postfach-Mails ingestieren (Outlook Graph oder IMAP aus DB-Konfiguration)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_VENV_PY = _ROOT / ".venv" / "Scripts" / "python.exe"


def _venv_hint() -> None:
    """Warnt wenn nicht das Projekt-venv aktiv ist."""
    if not _VENV_PY.exists():
        return
    try:
        if Path(sys.executable).resolve() != _VENV_PY.resolve():
            print(
                "Hinweis: .venv nicht aktiv. Nutze:\n"
                "  .\\.venv\\Scripts\\Activate.ps1\n"
                "  python scripts/run_outlook_ingest.py\n"
                "Oder: .\\scripts\\run_outlook_ingest.ps1",
                file=sys.stderr,
            )
    except OSError:
        return


def _import_error_help(exc: ModuleNotFoundError) -> None:
    """Zeigt Setup-Hinweis bei fehlenden Abhängigkeiten."""
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
    from backend.infrastructure.adapters.mail.ingestion import MailIngestionRunner
    from backend.infrastructure.adapters.outlook.ingestion import OutlookIngestionRunner
except ModuleNotFoundError as exc:
    _import_error_help(exc)
    raise SystemExit(1) from exc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    """Run the command workflow."""
    settings = get_settings()
    mode = settings.llm_mode.strip().lower()
    logger.info(
        "LLM_MODE=%s, OUTLOOK_FETCH_MAX=%s, unread_only=%s",
        mode,
        settings.outlook_fetch_max,
        settings.outlook_fetch_unread_only,
    )
    if mode == "mock":
        logger.warning(
            "LLM_MODE=mock: Klassifikation/Extraktion/Draft sind Platzhalter, "
            "keine echte KI-Qualitaet."
        )
    elif mode == "live":
        logger.info("LLM_MODE=live: OpenAI-API wird genutzt (Guthaben noetig).")
    ctx = build_app_context(settings)
    account_id = (settings.ingest_account_id or "").strip()
    if account_id:
        mail_record = ctx.mail_connection_repo.get(account_id)
        if mail_record is None:
            logger.error(
                "INGEST_ACCOUNT_ID=%s gesetzt, aber keine Postfach-Konfiguration "
                "in mail_connections. Bitte Onboarding abschließen.",
                account_id,
            )
            return 1
        runner = MailIngestionRunner(
            ctx.mail_connection_repo,
            ctx.workflow,
            ctx.email_repo,
            settings,
            ctx.account_repo,
            fetch_max=settings.outlook_fetch_max,
            fetch_unread_only=settings.outlook_fetch_unread_only,
        )
        mail_result = runner.run_for_account(account_id)
        for mail_item in mail_result.items:
            if mail_item.error:
                logger.error(
                    "message_id=%s error=%s",
                    mail_item.message_id,
                    mail_item.error,
                )
            elif mail_item.duplicate:
                logger.info("duplicate message_id=%s", mail_item.message_id)
            else:
                logger.info("ingested message_id=%s", mail_item.message_id)
        logger.info("Done: %s new ingest(s)", mail_result.processed)
        return 0

    outlook_runner = OutlookIngestionRunner.from_context(settings, ctx)
    outlook_result = outlook_runner.run()
    for outlook_item in outlook_result.items:
        if outlook_item.error:
            logger.error(
                "message_id=%s graph_id=%s error=%s",
                outlook_item.message_id,
                outlook_item.graph_id,
                outlook_item.error,
            )
        elif outlook_item.skipped_existing:
            logger.info("skip existing message_id=%s", outlook_item.message_id)
        elif outlook_item.duplicate:
            logger.info("duplicate message_id=%s", outlook_item.message_id)
        else:
            logger.info("ingested message_id=%s", outlook_item.message_id)
    logger.info("Done: %s new ingest(s)", outlook_result.processed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
