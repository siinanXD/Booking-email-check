"""Flask Application Factory."""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

from flask import Flask, g, jsonify
from flask_cors import CORS

from backend.api.auth.routes import auth_bp
from backend.api.auth.token_blocklist import MongoBlocklistBackend, configure
from backend.api.blueprints import register_api_blueprints
from backend.core.config.factory import AppContext, build_app_context
from backend.core.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> Flask:
    """Flask Application Factory.

    Verdrahtet Blueprints, CORS, Auth, Error-Handler und
    bindet den bestehenden AppContext (build_app_context) ein.
    """
    cfg = settings or get_settings()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = cfg.flask_secret_key or "dev-only-change-me"

    ctx = build_app_context(cfg)
    app.extensions["ctx"] = ctx
    configure(MongoBlocklistBackend(ctx.revoked_token_repo))

    origins = [o.strip() for o in cfg.cors_origins.split(",") if o.strip()]
    CORS(app, origins=origins, supports_credentials=True)

    @app.before_request
    def _bind_request_context() -> None:
        g.ctx = app.extensions["ctx"]
        g.settings = cfg

    @app.get("/health")
    def health() -> tuple[Any, int]:
        """Health-Check ohne Auth."""
        version = "0.1.0"
        try:
            import importlib.metadata

            version = importlib.metadata.version("email-platform")
        except Exception:
            pass
        return jsonify({"status": "ok", "version": version, "env": cfg.app_env}), 200

    app.register_blueprint(auth_bp)
    register_api_blueprints(app)

    from backend.api.blueprints.mail import complete_outlook_oauth_callback

    @app.get("/api/msal/callback")
    def msal_oauth_callback() -> Any:
        """Azure-Redirect-Alias (häufig in App-Registrierungen so eingetragen)."""
        return complete_outlook_oauth_callback()

    if cfg.flask_env == "production":
        static_dir = Path(cfg.frontend_build_dir)
        if not static_dir.is_absolute():
            static_dir = Path(__file__).resolve().parent.parent / static_dir
        if static_dir.is_dir():

            @app.route("/", defaults={"path": ""})
            @app.route("/<path:path>")
            def serve_spa(path: str) -> Any:
                """SPA-Static (Production)."""
                file_path = static_dir / path
                if file_path.is_file():
                    return app.send_static_file(path)
                return app.send_static_file("index.html")

            app.static_folder = str(static_dir)

    @app.errorhandler(404)
    def not_found(err: Any) -> tuple[Any, int]:
        """JSON 404."""
        _ = err
        return jsonify({"error": "Not found", "code": 404}), 404

    @app.errorhandler(500)
    def server_error(err: Any) -> tuple[Any, int]:
        """JSON 500."""
        logger.exception("Unhandled error: %s", err)
        return jsonify({"error": "Internal server error", "code": 500}), 500

    @app.errorhandler(Exception)
    def handle_exception(err: Exception) -> tuple[Any, int]:
        """Zentraler Exception-Handler."""
        if hasattr(err, "code") and isinstance(err.code, int):
            code = err.code
            return jsonify({"error": str(err), "code": code}), code
        logger.exception("API error")
        return jsonify({"error": str(err), "code": 500}), 500

    _start_dev_mail_poll(app, cfg)

    return app


def _start_dev_mail_poll(app: Flask, settings: Settings) -> None:
    """Startet Mail-Polling im Dev-Modus (Hintergrund-Thread)."""
    if settings.flask_env != "development":
        return
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    def _loop() -> None:
        from backend.features.mail.mail_poll_service import (
            build_mail_poll_service_from_context,
        )

        interval = max(30, settings.mail_poll_interval_seconds)
        logger.info("Dev mail poll thread started (interval=%ss)", interval)
        while True:
            try:
                with app.app_context():
                    ctx = app.extensions["ctx"]
                    service = build_mail_poll_service_from_context(ctx, settings)
                    result = service.run_all()
                    from backend.features.mail.mail_reprocess_service import (
                        build_mail_reprocess_service,
                    )

                    reprocess_svc = build_mail_reprocess_service(ctx)
                    reprocessed = 0
                    for summary in result.summaries:
                        batch = reprocess_svc.reprocess_stuck_bookings(
                            summary.account_id,
                            limit=5,
                        )
                        reprocessed += batch.completed
                    logger.info(
                        "Dev mail poll: accounts=%s processed=%s reprocessed=%s",
                        result.accounts_polled,
                        result.total_processed,
                        reprocessed,
                    )
            except Exception:
                logger.exception("Dev mail poll failed")
            time.sleep(interval)

    thread = threading.Thread(target=_loop, daemon=True, name="dev-mail-poll")
    thread.start()


def get_app_context(app: Flask) -> AppContext:
    """Typisierte Hilfe für Tests."""
    ctx = app.extensions.get("ctx")
    if not isinstance(ctx, AppContext):
        msg = "AppContext not initialized"
        raise RuntimeError(msg)
    return ctx
