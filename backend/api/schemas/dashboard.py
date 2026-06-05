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
    pending_grounding_review: int = 0
    reviewed_today: int = 0
    last_sync_at: str | None = None
    last_email_received_at: str | None = None
    last_booking_detected_at: str | None = None
    mail_fetch_unread_only: bool = False
    nav_bookings: int = 0
    nav_cancellations: int = 0
    nav_changes: int = 0
    nav_messages: int = 0
    nav_ground_zero: int = 0
    nav_completed: int = 0
