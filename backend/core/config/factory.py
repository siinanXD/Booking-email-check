"""Zentrale Verdrahtung: Settings → Services → Workflow."""

from __future__ import annotations

from dataclasses import dataclass

from backend.ai.services.classification import ClassificationService, LLMClient
from backend.ai.services.entity_resolution import EntityResolutionService
from backend.ai.services.extraction import ExtractionService
from backend.ai.services.gemini_client import GeminiClientProtocol
from backend.ai.services.gemini_factory import build_gemini_client
from backend.ai.services.grounding import GroundingService
from backend.ai.services.indexing import EmbeddingClient, EmbeddingFn, IndexingService
from backend.ai.services.ingestion import IngestionService
from backend.ai.services.openai_client import OpenAIClient
from backend.ai.services.response_generation import ResponseGenerationService
from backend.ai.services.retrieval import RetrievalService
from backend.ai.services.similarity_search import SimilaritySearchService
from backend.ai.services.tenant_workflow_runtime import (
    TenantWorkflowExecutor,
    WorkflowRouter,
)
from backend.ai.services.triage import TriageService
from backend.ai.services.validation import ValidationService
from backend.ai.workflows.checkpointer import build_checkpointer
from backend.ai.workflows.email_workflow import EmailWorkflow
from backend.application.ingestion import IngestionRouter
from backend.application.review import ReviewRouter
from backend.core.config.settings import Settings, get_settings
from backend.features.notifications.notification_service import NotificationService
from backend.infrastructure.observability.alerts import AlertService
from backend.infrastructure.observability.langfuse_client import LangfuseTracer
from backend.infrastructure.observability.langfuse_setup import (
    configure_langfuse_env,
    tracing_enabled,
)
from backend.infrastructure.observability.mail_cost import MailCostTracker
from backend.infrastructure.observability.review_feedback import ReviewFeedbackTracker
from backend.infrastructure.repositories.account_repository import AccountRepository
from backend.infrastructure.repositories.admin_audit_log_repository import (
    AdminAuditLogRepository,
)
from backend.infrastructure.repositories.chunk_repository import ChunkRepository
from backend.infrastructure.repositories.email_repository import EmailRepository
from backend.infrastructure.repositories.embedding_repository import EmbeddingRepository
from backend.infrastructure.repositories.entity_repository import EntityRepository
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
from backend.infrastructure.repositories.mongo import Db, get_database
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
from backend.infrastructure.repositories.platform_llm_prompt_history_repository import (
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
    platform_admin_config_repo: PlatformAdminConfigRepository
    indexing_service: IndexingService | None = None
    gemini_client: GeminiClientProtocol | None = None


def build_app_context(settings: Settings | None = None) -> AppContext:
    """Erzeugt den Anwendungskontext aus Settings."""
    cfg = settings or get_settings()
    db = get_database(cfg)

    email_repo = EmailRepository(db)
    entity_repo = EntityRepository(db)
    extraction_repo = ExtractionRepository(db)
    embedding_repo = EmbeddingRepository(db)
    chunk_repo = ChunkRepository(db)
    review_repo = ReviewRepository(db)
    metrics_repo = MailMetricsRepository(db)
    user_repo = UserRepository(db)
    account_repo = AccountRepository(db)
    revoked_token_repo = RevokedTokenRepository(db)
    notification_repo = NotificationRepository(db)
    property_recipient_repo = PropertyRecipientRepository(db)
    platform_settings_repo = PlatformSettingsRepository(db)
    mail_connection_repo = MailConnectionRepository(db)
    outlook_oauth_flow_repo = OutlookOAuthFlowRepository(db)
    platform_llm_config_repo = PlatformLlmConfigRepository(db)
    platform_llm_prompt_history_repo = PlatformLlmPromptHistoryRepository(db)
    tenant_workflow_repo = TenantWorkflowRepository(db)
    admin_audit_log_repo = AdminAuditLogRepository(db)
    mail_summary_repo = MailSummaryRepository(db)
    tenant_learned_examples_repo = TenantLearnedExamplesRepository(db)
    support_ticket_repo = SupportTicketRepository(db)
    platform_admin_config_repo = PlatformAdminConfigRepository(db)
    notification_service = NotificationService(
        cfg,
        notification_repo,
        user_repo,
        property_recipient_repo,
        platform_settings_repo,
    )

    alerts = AlertService(webhook_url=cfg.webhook_alert_url)
    tracing = configure_langfuse_env(cfg) and tracing_enabled(cfg)
    langfuse_tracer = LangfuseTracer(
        enabled=tracing,
        public_key=cfg.langfuse_public_key or None,
        secret_key=cfg.langfuse_secret_key or None,
        host=cfg.langfuse_host,
    )
    feedback_tracker = ReviewFeedbackTracker(alerts=alerts)

    llm_mode = cfg.llm_mode.strip().lower()
    # Raw mail prompts must not be auto-captured by provider wrappers.
    use_langfuse_openai = False
    llm: LLMClient
    embed_client: EmbeddingFn
    if llm_mode == "mock":
        from backend.ai.testing.mock_llm import MockEmbeddingClient, MockLLM

        llm = MockLLM()
        embed_client = MockEmbeddingClient()
    elif llm_mode == "live":
        llm = OpenAIClient(cfg.openai_api_key, use_langfuse=use_langfuse_openai)
        embed_client = EmbeddingClient(
            cfg.openai_api_key,
            cfg.embedding_model,
            use_langfuse=use_langfuse_openai,
            tracing=tracing,
        )
    else:
        msg = f"Unsupported LLM_MODE: {cfg.llm_mode!r} (use live or mock)"
        raise ValueError(msg)
    mail_cost = MailCostTracker(
        alerts=alerts,
        tracing=tracing,
        metrics_repo=metrics_repo,
    )
    triage = TriageService(
        llm=llm,
        model=cfg.openai_model_triage,
        triage_llm_enabled=cfg.triage_llm_enabled,
        max_body_chars=cfg.triage_llm_max_body_chars,
        tracing=tracing,
        alerts=alerts,
        mail_cost=mail_cost,
    )
    ingestion = IngestionService(email_repo, triage)
    indexing = IndexingService(embedding_repo, embed_client, chunk_repo, alerts=alerts)
    classification = ClassificationService(
        llm,
        cfg.openai_model_classify,
        tracing=tracing,
        alerts=alerts,
        mail_cost=mail_cost,
        llm_config_repo=platform_llm_config_repo,
        learned_examples_repo=tenant_learned_examples_repo,
    )
    extraction = ExtractionService(
        llm,
        cfg.openai_model_extract,
        tracing=tracing,
        alerts=alerts,
        mail_cost=mail_cost,
        llm_config_repo=platform_llm_config_repo,
    )
    validation = ValidationService()
    similarity = SimilaritySearchService(
        embedding_repo,
        embed_client,
        use_atlas=cfg.similarity_use_atlas,
    )
    entity_resolution = EntityResolutionService(entity_repo)
    retrieval = RetrievalService(
        entity_repo,
        email_repo,
        similarity=similarity,
        entity_resolution=entity_resolution,
        alerts=alerts,
        llm_config_repo=platform_llm_config_repo,
    )
    response_gen = ResponseGenerationService(
        llm,
        cfg.openai_model_draft,
        retrieval,
        GroundingService(),
        tracing=tracing,
        alerts=alerts,
        mail_cost=mail_cost,
        llm_config_repo=platform_llm_config_repo,
    )
    gemini_client = build_gemini_client(cfg)
    workflow_router = WorkflowRouter(tenant_workflow_repo)
    tenant_workflow_executor = TenantWorkflowExecutor(
        llm,
        classify_model=cfg.openai_model_classify,
        extract_model=cfg.openai_model_extract,
        gemini=gemini_client,
        gemini_extract_model=cfg.gemini_model_extract,
    )

    checkpointer = build_checkpointer(cfg)
    workflow = EmailWorkflow(
        ingestion=ingestion,
        classification=classification,
        extraction=extraction,
        validation=validation,
        retrieval=retrieval,
        response_gen=response_gen,
        email_repo=email_repo,
        extraction_repo=extraction_repo,
        indexing=indexing,
        alerts=alerts,
        mail_cost=mail_cost,
        review_repo=review_repo,
        notification_service=notification_service,
        checkpointer=checkpointer,
        feedback_tracker=feedback_tracker,
        langfuse_tracer=langfuse_tracer,
        workflow_router=workflow_router,
        tenant_workflow_executor=tenant_workflow_executor,
        tenant_workflow_repo=tenant_workflow_repo,
        tracing=tracing,
    )

    return AppContext(
        settings=cfg,
        db=db,
        ingestion_router=IngestionRouter(ingestion),
        review_router=ReviewRouter(workflow),
        workflow=workflow,
        email_repo=email_repo,
        extraction_repo=extraction_repo,
        review_repo=review_repo,
        metrics_repo=metrics_repo,
        user_repo=user_repo,
        account_repo=account_repo,
        revoked_token_repo=revoked_token_repo,
        platform_settings_repo=platform_settings_repo,
        property_recipient_repo=property_recipient_repo,
        mail_connection_repo=mail_connection_repo,
        outlook_oauth_flow_repo=outlook_oauth_flow_repo,
        platform_llm_config_repo=platform_llm_config_repo,
        platform_llm_prompt_history_repo=platform_llm_prompt_history_repo,
        tenant_workflow_repo=tenant_workflow_repo,
        admin_audit_log_repo=admin_audit_log_repo,
        mail_summary_repo=mail_summary_repo,
        tenant_learned_examples_repo=tenant_learned_examples_repo,
        support_ticket_repo=support_ticket_repo,
        platform_admin_config_repo=platform_admin_config_repo,
        indexing_service=indexing,
        gemini_client=gemini_client,
    )
