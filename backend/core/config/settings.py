"""Zentrale Einstellungen aus Umgebungsvariablen (Pydantic Settings)."""

from __future__ import annotations

from pathlib import Path
from typing import Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Immer Projekt-`.env`, nicht abhaengig vom aktuellen Terminal-Verzeichnis
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Lädt Werte aus `.env`; siehe `.env.example` für alle Keys."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    # live = OpenAI; mock = Dev ohne API-Kosten (Platzhalter-Antworten)
    llm_mode: str = Field(default="live", alias="LLM_MODE")
    mongodb_uri: str = Field(alias="MONGODB_URI")
    mongodb_db_name: str = Field(default="ai_email", alias="MONGODB_DB_NAME")

    langfuse_public_key: str = Field(alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        alias="LANGFUSE_HOST",
    )
    langfuse_project_id: str = Field(default="", alias="LANGFUSE_PROJECT_ID")

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    human_review_required: bool = Field(default=True, alias="HUMAN_REVIEW_REQUIRED")

    openai_model_classify: str = Field(
        default="gpt-4o-mini",
        alias="OPENAI_MODEL_CLASSIFY",
    )
    openai_model_extract: str = Field(
        default="gpt-4o-mini",
        alias="OPENAI_MODEL_EXTRACT",
    )
    openai_model_draft: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL_DRAFT")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model_extract: str = Field(
        default="gemini-2.0-flash",
        alias="GEMINI_MODEL_EXTRACT",
    )
    openai_model_triage: str = Field(
        default="gpt-4o-mini",
        alias="OPENAI_MODEL_TRIAGE",
    )
    triage_llm_enabled: bool = Field(default=True, alias="TRIAGE_LLM_ENABLED")
    triage_llm_max_body_chars: int = Field(
        default=2000,
        alias="TRIAGE_LLM_MAX_BODY_CHARS",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="EMBEDDING_MODEL",
    )
    similarity_use_atlas: bool = Field(default=False, alias="SIMILARITY_USE_ATLAS")
    max_tokens_per_mail: int = Field(default=8000, alias="MAX_TOKENS_PER_MAIL")
    webhook_alert_url: str | None = Field(default=None, alias="WEBHOOK_ALERT_URL")
    langgraph_checkpoint_uri: str | None = Field(
        default=None,
        alias="LANGGRAPH_CHECKPOINT_URI",
    )

    azure_tenant_id: str | None = Field(default=None, alias="AZURE_TENANT_ID")
    azure_client_id: str | None = Field(default=None, alias="AZURE_CLIENT_ID")
    azure_client_secret: str | None = Field(default=None, alias="AZURE_CLIENT_SECRET")
    azure_authority: str = Field(default="common", alias="AZURE_AUTHORITY")
    outlook_mailbox: str | None = Field(default=None, alias="OUTLOOK_MAILBOX")
    outlook_auth_mode: str = Field(default="delegated", alias="OUTLOOK_AUTH_MODE")
    outlook_token_cache_path: str = Field(
        default=".outlook_token_cache.json",
        alias="OUTLOOK_TOKEN_CACHE_PATH",
    )
    outlook_post_action: str = Field(default="none", alias="OUTLOOK_POST_ACTION")
    outlook_processed_folder: str | None = Field(
        default=None,
        alias="OUTLOOK_PROCESSED_FOLDER",
    )
    outlook_fetch_max: int = Field(default=100, alias="OUTLOOK_FETCH_MAX")
    outlook_fetch_unread_only: bool = Field(
        default=False,
        alias="OUTLOOK_FETCH_UNREAD_ONLY",
    )

    flask_secret_key: str = Field(default="", alias="FLASK_SECRET_KEY")
    admin_email: str = Field(default="admin@example.com", alias="ADMIN_EMAIL")
    admin_password: str = Field(default="", alias="ADMIN_PASSWORD")
    jwt_access_expires: int = Field(default=3600, alias="JWT_ACCESS_TOKEN_EXPIRES")
    jwt_refresh_expires: int = Field(
        default=604800,
        alias="JWT_REFRESH_TOKEN_EXPIRES",
    )
    cors_origins: str = Field(
        default="http://localhost:5173",
        alias="CORS_ORIGINS",
    )
    frontend_url_env: str = Field(default="", alias="FRONTEND_URL")
    outlook_oauth_redirect_uri_env: str = Field(
        default="",
        alias="OUTLOOK_OAUTH_REDIRECT_URI",
    )
    flask_env: str = Field(default="development", alias="FLASK_ENV")
    flask_port: int = Field(default=5000, alias="FLASK_PORT")
    frontend_build_dir: str = Field(
        default="frontend/dist",
        alias="FRONTEND_BUILD_DIR",
    )
    web_demo_data: bool = Field(default=False, alias="WEB_DEMO_DATA")
    web_use_memory_checkpointer: bool | None = Field(
        default=None,
        alias="WEB_USE_MEMORY_CHECKPOINTER",
    )

    whatsapp_enabled: bool = Field(default=False, alias="WHATSAPP_ENABLED")
    whatsapp_access_token: str = Field(default="", alias="WHATSAPP_ACCESS_TOKEN")
    whatsapp_phone_number_id: str = Field(default="", alias="WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_api_version: str = Field(default="v21.0", alias="WHATSAPP_API_VERSION")
    whatsapp_template_language: str = Field(
        default="de",
        alias="WHATSAPP_TEMPLATE_LANGUAGE",
    )
    whatsapp_template_cleaning_task: str = Field(
        default="booking_cleaning_task_de",
        alias="WHATSAPP_TEMPLATE_CLEANING_TASK",
    )
    whatsapp_template_status_notice: str = Field(
        default="booking_status_notice_de",
        alias="WHATSAPP_TEMPLATE_STATUS_NOTICE",
    )
    whatsapp_template_guest_inquiry: str = Field(
        default="booking_guest_inquiry_de",
        alias="WHATSAPP_TEMPLATE_GUEST_INQUIRY",
    )
    whatsapp_default_recipients: str = Field(
        default="",
        alias="WHATSAPP_DEFAULT_RECIPIENTS",
    )
    whatsapp_test_recipient: str = Field(
        default="",
        alias="WHATSAPP_TEST_RECIPIENT",
    )
    whatsapp_auto_on_detect: bool = Field(
        default=False,
        alias="WHATSAPP_AUTO_ON_DETECT",
    )
    whatsapp_template_support_ticket: str = Field(
        default="platform_support_ticket_de",
        alias="WHATSAPP_TEMPLATE_SUPPORT_TICKET",
    )
    platform_admin_whatsapp_e164: str = Field(
        default="",
        alias="PLATFORM_ADMIN_WHATSAPP_E164",
    )
    mail_ingest_initial_lookback: int = Field(
        default=50,
        alias="MAIL_INGEST_INITIAL_LOOKBACK",
    )
    mail_ingest_initial_fetch_cap: int = Field(
        default=120,
        alias="MAIL_INGEST_INITIAL_FETCH_CAP",
    )
    ingest_account_id: str | None = Field(default=None, alias="INGEST_ACCOUNT_ID")
    mail_poll_interval_seconds: int = Field(
        default=300, alias="MAIL_POLL_INTERVAL_SECONDS"
    )
    mail_poll_run_once: bool = Field(default=False, alias="MAIL_POLL_RUN_ONCE")

    @model_validator(mode="after")
    def apply_dev_defaults(self) -> Self:
        """Dev: Memory-Checkpointer wenn Env-Var nicht gesetzt."""
        if self.web_use_memory_checkpointer is None:
            self.web_use_memory_checkpointer = self.app_env == "development"
        return self

    @field_validator("mongodb_uri")
    @classmethod
    def validate_mongodb_uri(cls, value: str) -> str:
        """URI muss ein gültiges MongoDB-Schema verwenden."""
        if not value.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("MONGODB_URI must start with mongodb:// or mongodb+srv://")
        return value

    @property
    def frontend_url(self) -> str:
        """Basis-URL des React-Frontends (OAuth-Rückleitung)."""
        if self.frontend_url_env.strip():
            return self.frontend_url_env.strip().rstrip("/")
        first = self.cors_origins.split(",")[0].strip()
        return first.rstrip("/") if first else "http://localhost:5173"

    @property
    def outlook_oauth_redirect_uri(self) -> str:
        """Redirect-URI für Microsoft OAuth (Backend-Callback)."""
        if self.outlook_oauth_redirect_uri_env.strip():
            return self.outlook_oauth_redirect_uri_env.strip().replace(
                "127.0.0.1", "localhost"
            )
        return f"http://localhost:{self.flask_port}/api/mail/outlook/callback"


def get_settings() -> Settings:
    """Factory für Settings; lädt Werte aus Umgebung / `.env`."""
    return Settings.model_validate({})
