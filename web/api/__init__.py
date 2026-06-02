"""REST-API-Blueprints."""

from __future__ import annotations

from flask import Flask

from web.api.bookings import bookings_bp
from web.api.costs import costs_bp
from web.api.dashboard import dashboard_bp
from web.api.emails import emails_bp
from web.api.review import review_bp


def register_api_blueprints(app: Flask) -> None:
    """Registriert alle geschützten API-Blueprints."""
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(emails_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(costs_bp)
