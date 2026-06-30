"""Hintergrund-Jobs (Daemon-Threads) der Web-App."""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import UTC, datetime

from flask import Flask

from backend.core.config.settings import Settings

logger = logging.getLogger(__name__)


def start_cleaning_reminders(app: Flask, settings: Settings) -> None:
    """Startet den Putz-Erinnerungs-Job als Hintergrund-Thread (Vortags-WhatsApp)."""
    if not settings.cleaning_reminders_in_web:
        return
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    def _loop() -> None:
        from backend.features.cleaning.reminder_service import (
            build_cleaning_reminder_service,
        )

        interval = max(300, settings.cleaning_reminder_interval_seconds)
        logger.info("Cleaning reminder thread started (interval=%ss)", interval)
        while True:
            try:
                with app.app_context():
                    ctx = app.extensions["ctx"]
                    service = build_cleaning_reminder_service(ctx)
                    if service is not None:
                        now = datetime.now(UTC)
                        sent = service.run_all(today=now.date(), now_hour=now.hour)
                        if sent:
                            logger.info("Cleaning reminders sent: %s", sent)
            except Exception:
                logger.exception("Cleaning reminder run failed")
            time.sleep(interval)

    thread = threading.Thread(target=_loop, daemon=True, name="cleaning-reminders")
    thread.start()
