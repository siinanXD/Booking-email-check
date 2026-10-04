"""Sentry-Initialisierung und PII-Scrubbing (keine personenbezogenen Daten)."""

from __future__ import annotations

import logging
from typing import Any

from backend.core.config.settings import Settings

logger = logging.getLogger(__name__)


def _mask_key(container: dict[str, Any], key: str, mask: Any) -> None:
    if container.get(key):
        container[key] = mask(str(container[key]))


def _strip_frame_vars(stacktrace: Any) -> None:
    if not isinstance(stacktrace, dict):
        return
    for frame in stacktrace.get("frames") or []:
        if isinstance(frame, dict):
            frame.pop("vars", None)


def _scrub_sentry_event(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    """Maskiert E-Mail/Telefon und entfernt Variablen/Extras (PII-Schutz)."""
    from backend.core.utils.pii import mask_pii

    try:
        _mask_key(event, "message", mask_pii)
        for exc in (event.get("exception") or {}).get("values") or []:
            _mask_key(exc, "value", mask_pii)
            _strip_frame_vars(exc.get("stacktrace"))
        for thread in (event.get("threads") or {}).get("values") or []:
            _strip_frame_vars(thread.get("stacktrace"))
        for crumb in (event.get("breadcrumbs") or {}).get("values") or []:
            _mask_key(crumb, "message", mask_pii)
        logentry = event.get("logentry")
        if isinstance(logentry, dict):
            _mask_key(logentry, "message", mask_pii)
            _mask_key(logentry, "formatted", mask_pii)
            logentry.pop("params", None)
        event.pop("extra", None)
    except Exception:  # noqa: BLE001 - Scrubbing darf den Report nie blockieren
        pass
    return event


def _init_sentry(cfg: Settings) -> None:
    """Initialisiert Sentry nur, wenn ein DSN gesetzt ist (sonst no-op)."""
    if not cfg.sentry_dsn:
        return
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration

    sentry_sdk.init(
        dsn=cfg.sentry_dsn,
        environment=cfg.app_env,
        integrations=[FlaskIntegration()],
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        traces_sample_rate=cfg.sentry_traces_sample_rate,
        before_send=_scrub_sentry_event,  # type: ignore[arg-type, unused-ignore]
    )
    logger.info("Sentry error tracking aktiv (env=%s)", cfg.app_env)
