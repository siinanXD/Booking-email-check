"""Web-Prozess pollt nur bei MAIL_POLL_IN_WEB=true (kein Doppel-Polling)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from backend.api import app as appmod


def test_start_mail_poll_skipped_when_disabled(monkeypatch) -> None:
    thread = MagicMock()
    monkeypatch.setattr(appmod.threading, "Thread", thread)
    cfg = SimpleNamespace(mail_poll_in_web=False, mail_poll_interval_seconds=300)
    appmod._start_mail_poll(SimpleNamespace(debug=False), cfg)  # type: ignore[arg-type]
    thread.assert_not_called()


def test_start_mail_poll_runs_when_enabled(monkeypatch) -> None:
    thread = MagicMock()
    monkeypatch.setattr(appmod.threading, "Thread", thread)
    cfg = SimpleNamespace(
        mail_poll_in_web=True,
        mail_poll_interval_seconds=300,
        mail_poll_max_workers=1,
    )
    appmod._start_mail_poll(SimpleNamespace(debug=False), cfg)  # type: ignore[arg-type]
    thread.assert_called_once()
    thread.return_value.start.assert_called_once()
