"""REST-API-Blueprints."""

from __future__ import annotations

from flask import Flask

from backend.api.blueprints.admin import admin_bp
from backend.api.blueprints.bookings import bookings_bp
from backend.api.blueprints.costs import costs_bp
from backend.api.blueprints.dashboard import dashboard_bp
from backend.api.blueprints.emails import emails_bp
from backend.api.blueprints.mail import mail_bp
from backend.api.blueprints.properties import properties_bp
from backend.api.blueprints.review import review_bp
from backend.api.blueprints.settings import settings_bp
from backend.api.blueprints.support_tickets import admin_support_bp, support_bp
from backend.api.blueprints.workflows import workflows_bp


def register_api_blueprints(app: Flask) -> None:
    """Registriert alle geschützten API-Blueprints."""
    app.register_blueprint(admin_bp)
    app.register_blueprint(support_bp)
    app.register_blueprint(admin_support_bp)
    app.register_blueprint(mail_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(emails_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(costs_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(properties_bp)
    app.register_blueprint(workflows_bp)
