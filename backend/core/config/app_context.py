"""AppContext dataclass — alle verdrahteten Komponenten für API/CLI/Tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.ai.services.classification import LLMClient
    from backend.ai.services.gemini_client import GeminiClientProtocol
    from backend.ai.services.indexing import IndexingService
    from backend.ai.workflows.email_workflow import EmailWorkflow
    from backend.application.ingestion import IngestionRouter
    from backend.application.review import ReviewRouter
    from backend.core.config.settings import Settings
    from backend.features.billing.entitlement_service import EntitlementService
    from backend.features.billing.stripe_service import StripeService
    from backend.features.billing.stripe_webhook import StripeWebhookHandler
    from backend.features.cleaning.service import CleaningScheduleService
    from backend.features.notifications.notification_service import NotificationService
    from backend.infrastructure.repositories.account_repository import AccountRepository
    from backend.infrastructure.repositories.admin_audit_log_repository import (
        AdminAuditLogRepository,
    )
    from backend.infrastructure.repositories.cleaning_partner_repository import (
        CleaningPartnerRepository,
    )
    from backend.infrastructure.repositories.cleaning_task_repository import (
        CleaningTaskRepository,
    )
    from backend.infrastructure.repositories.email_repository import EmailRepository
    from backend.infrastructure.repositories.extraction_repository import (
        ExtractionRepository,
    )
    from backend.infrastructure.repositories.mail_connection_repository import (
        MailConnectionRepository,
    )
    from backend.infrastructure.repositories.mail_metrics_repository import (
        MailMetricsRepository,
    )
    from backend.infrastructure.repositories.mail_summary_repository import (
        MailSummaryRepository,
    )
    from backend.infrastructure.repositories.mongo import Db
    from backend.infrastructure.repositories.notification_repository import (
        NotificationRepository,
    )
    from backend.infrastructure.repositories.outlook_oauth_flow_repository import (
        OutlookOAuthFlowRepository,
    )
    from backend.infrastructure.repositories.platform_admin_config_repository import (
        PlatformAdminConfigRepository,
    )
    from backend.infrastructure.repositories.platform_llm_config_repository import (
        PlatformLlmConfigRepository,
    )
    from backend.infrastructure.repositories.platform_llm_prompt_history_repository import (  # noqa: E501
        PlatformLlmPromptHistoryRepository,
    )
    from backend.infrastructure.repositories.platform_settings_repository import (
        PlatformSettingsRepository,
    )
    from backend.infrastructure.repositories.property_recipient_repository import (
        PropertyRecipientRepository,
    )
    from backend.infrastructure.repositories.review_repository import ReviewRepository
    from backend.infrastructure.repositories.revoked_token_repository import (
        RevokedTokenRepository,
    )
    from backend.infrastructure.repositories.subscription_repository import (
        SubscriptionRepository,
    )
    from backend.infrastructure.repositories.support_ticket_repository import (
        SupportTicketRepository,
    )
    from backend.infrastructure.repositories.tenant_learned_examples_repository import (
        TenantLearnedExamplesRepository,
    )
    from backend.infrastructure.repositories.tenant_workflow_repository import (
        TenantWorkflowRepository,
    )
    from backend.infrastructure.repositories.user_repository import UserRepository


@dataclass
class AppContext:
    """Alle verdrahteten Komponenten für API/CLI/Tests."""

    settings: Settings
    db: Db
    ingestion_router: IngestionRouter
    review_router: ReviewRouter
    workflow: EmailWorkflow
    email_repo: EmailRepository
    extraction_repo: ExtractionRepository
    review_repo: ReviewRepository
    metrics_repo: MailMetricsRepository
    user_repo: UserRepository
    account_repo: AccountRepository
    revoked_token_repo: RevokedTokenRepository
    platform_settings_repo: PlatformSettingsRepository
    property_recipient_repo: PropertyRecipientRepository
    mail_connection_repo: MailConnectionRepository
    outlook_oauth_flow_repo: OutlookOAuthFlowRepository
    platform_llm_config_repo: PlatformLlmConfigRepository
    platform_llm_prompt_history_repo: PlatformLlmPromptHistoryRepository
    tenant_workflow_repo: TenantWorkflowRepository
    admin_audit_log_repo: AdminAuditLogRepository
    mail_summary_repo: MailSummaryRepository
    tenant_learned_examples_repo: TenantLearnedExamplesRepository
    support_ticket_repo: SupportTicketRepository
    subscription_repo: SubscriptionRepository
    platform_admin_config_repo: PlatformAdminConfigRepository
    notification_repo: NotificationRepository
    indexing_service: IndexingService | None = None
    gemini_client: GeminiClientProtocol | None = None
    llm: LLMClient | None = None
    cleaning_partner_repo: CleaningPartnerRepository | None = None
    cleaning_task_repo: CleaningTaskRepository | None = None
    cleaning_service: CleaningScheduleService | None = None
    notification_service: NotificationService | None = None
    entitlement_service: EntitlementService | None = None
    stripe_service: StripeService | None = None
    stripe_webhook_handler: StripeWebhookHandler | None = None
