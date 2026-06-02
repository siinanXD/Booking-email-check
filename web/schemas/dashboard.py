"""Dashboard-API-Schemas."""

from __future__ import annotations

from pydantic import BaseModel


class DashboardStats(BaseModel):
    """KPI-Übersicht."""

    total_emails_today: int = 0
    total_emails_week: int = 0
    pending_review: int = 0
    processed_today: int = 0
    spam_discarded_today: int = 0
    new_bookings_today: int = 0
    cancellations_today: int = 0
    changes_today: int = 0
    booking_emails_total: int = 0
    booking_emails_week: int = 0
    cost_today_usd: float = 0.0
    cost_week_usd: float = 0.0
    avg_cost_per_mail_usd: float = 0.0
    grounding_failures_today: int = 0
