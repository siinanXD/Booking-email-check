"""Admin-Monitoring-Schemas (Phase 3)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from backend.api.schemas.accounts import AccountListItem
from backend.api.schemas.costs import CostSeriesPoint

ActivityStatus = Literal["active", "idle", "never"]


class AdminUserSummary(BaseModel):
    """Benutzer eines Mandanten (ohne Secrets)."""

    id: str
    email: str
    role: str
    created_at: str


class MailConnectionSummary(BaseModel):
    """Kurzstatus Postfach-Verbindung."""

    provider: str
    status: str
    email_address: str = ""
    connected: bool = False
    last_sync_at: str | None = None
    last_error: str | None = None
    onboarding_completed: bool = False


class AdminTenantRow(BaseModel):
    """Zeile in der Mandanten-Übersicht."""

    account: AccountListItem
    activity_status: ActivityStatus
    costs_30d_usd: float = 0.0
    tokens_30d: int = 0
    mails_processed_30d: int = 0
    last_sync_at: str | None = None
    last_mail_received_at: str | None = None


class AdminOverviewResponse(BaseModel):
    """Plattform-KPIs + Mandanten-Tabelle."""

    total_accounts: int = 0
    pending_accounts: int = 0
    active_accounts: int = 0
    active_users_7d: int = 0
    total_cost_usd_30d: float = 0.0
    total_tokens_30d: int = 0
    mails_processed_30d: int = 0
    tenants: list[AdminTenantRow] = Field(default_factory=list)


class AdminAccountDetailResponse(BaseModel):
    """Mandanten-Drill-down."""

    account: AccountListItem
    users: list[AdminUserSummary] = Field(default_factory=list)
    mail_connection: MailConnectionSummary | None = None
    activity_status: ActivityStatus = "never"
    db_counts: dict[str, int] = Field(default_factory=dict)
    costs_30d_usd: float = 0.0
    tokens_30d: int = 0
    mails_processed_30d: int = 0
    last_mail_received_at: str | None = None
    latest_correlation_id: str | None = None
    langfuse_session_url: str | None = None


class AdminAccountCostRow(BaseModel):
    """Kosten pro Mandant."""

    account_id: str
    display_name: str
    cost_usd: float = 0.0
    total_tokens: int = 0
    mail_count: int = 0


class AdminExpensiveMailRow(BaseModel):
    """Teure Mail für Observability."""

    correlation_id: str
    account_id: str | None = None
    cost_usd: float = 0.0
    total_tokens: int = 0
    processed_at: str
    langfuse_session_url: str | None = None


class AdminCostsMetricsResponse(BaseModel):
    """Cross-Tenant Kosten."""

    days: int = 30
    series: list[CostSeriesPoint] = Field(default_factory=list)
    total_usd: float = 0.0
    unassigned_cost_usd: float = 0.0
    by_account: list[AdminAccountCostRow] = Field(default_factory=list)
    top_mails: list[AdminExpensiveMailRow] = Field(default_factory=list)


class AdminTokensMetricsResponse(BaseModel):
    """Cross-Tenant Token-Aggregation."""

    days: int = 30
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    by_account: list[AdminAccountCostRow] = Field(default_factory=list)


class AdminPublicConfigResponse(BaseModel):
    """Nicht-sensitive Admin-Konfiguration für die UI."""

    langfuse_host: str
    langfuse_project_id: str | None = None
    langfuse_tracing_enabled: bool = False
