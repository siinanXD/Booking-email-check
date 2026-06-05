"""Tenant-Workflow API-Schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.core.models.workflow_media import (
    MAX_ATTACHMENTS_PER_REQUEST,
    WorkflowMediaAttachment,
)

WorkflowImportance = Literal["high", "medium", "low"]
WorkflowLlmProvider = Literal["openai", "gemini"]


class WorkflowMatchRulesSchema(BaseModel):
    subject_keywords: list[str] = Field(default_factory=list)
    from_domains: list[str] = Field(default_factory=list)
    body_keywords: list[str] = Field(default_factory=list)


class WorkflowTestEmailSchema(BaseModel):
    subject: str
    body: str
    expected_fields: dict[str, Any] | None = None
    attachments: list[WorkflowMediaAttachment] = Field(default_factory=list)

    @field_validator("attachments")
    @classmethod
    def validate_attachments(
        cls, value: list[WorkflowMediaAttachment]
    ) -> list[WorkflowMediaAttachment]:
        if len(value) > MAX_ATTACHMENTS_PER_REQUEST:
            msg = f"At most {MAX_ATTACHMENTS_PER_REQUEST} attachments per test email"
            raise ValueError(msg)
        return value


class WorkflowFewShotExampleSchema(BaseModel):
    subject: str
    body: str
    expected_json: dict[str, Any] = Field(default_factory=dict)


class TenantWorkflowSummary(BaseModel):
    id: str
    slug: str
    label: str
    description: str
    enabled: bool
    sandbox_only: bool
    importance: WorkflowImportance
    supports_multimodal: bool
    test_email_count: int
    tests_passed: bool = False
    updated_at: str


class TenantWorkflowListResponse(BaseModel):
    items: list[TenantWorkflowSummary]


class TenantWorkflowNavItem(BaseModel):
    """Öffentliche Nav-Metadaten für Mandanten (nur Live-Workflows)."""

    id: str
    slug: str
    label: str
    description: str


class TenantWorkflowNavResponse(BaseModel):
    items: list[TenantWorkflowNavItem]


class TenantWorkflowResponse(BaseModel):
    id: str
    account_id: str
    slug: str
    label: str
    description: str
    enabled: bool
    sandbox_only: bool
    priority: int
    search_hints: str
    importance: WorkflowImportance
    required_fields: list[str]
    optional_fields: list[str]
    extraction_schema: dict[str, Any]
    classify_prompt: str
    extract_prompt: str
    draft_prompt: str
    few_shot_examples: list[WorkflowFewShotExampleSchema]
    test_emails: list[WorkflowTestEmailSchema]
    match_rules: WorkflowMatchRulesSchema
    llm_provider: WorkflowLlmProvider
    supports_multimodal: bool
    multimodal_prompt: str
    last_test_passed_at: str | None = None
    last_test_passed_count: int = 0
    last_test_passed_total: int = 0
    created_by_user_id: str | None
    updated_by_user_id: str | None
    created_at: str
    updated_at: str
    version: int


class TenantWorkflowCreateRequest(BaseModel):
    label: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=80)
    description: str = ""
    search_hints: str = ""
    importance: WorkflowImportance = "medium"
    required_fields: list[str] = Field(default_factory=list)
    optional_fields: list[str] = Field(default_factory=list)
    extraction_schema: dict[str, Any] = Field(default_factory=dict)
    classify_prompt: str = ""
    extract_prompt: str = ""
    draft_prompt: str = ""
    few_shot_examples: list[WorkflowFewShotExampleSchema] = Field(default_factory=list)
    test_emails: list[WorkflowTestEmailSchema] = Field(default_factory=list)
    match_rules: WorkflowMatchRulesSchema = Field(
        default_factory=WorkflowMatchRulesSchema
    )
    llm_provider: WorkflowLlmProvider = "openai"
    supports_multimodal: bool = False
    multimodal_prompt: str = ""
    enabled: bool = False
    sandbox_only: bool = True
    priority: int = 0


class TenantWorkflowUpdateRequest(TenantWorkflowCreateRequest):
    """PUT-Body — gleiche Felder wie Create."""


class TenantWorkflowSuggestRequest(BaseModel):
    """Beschreibung und/oder Beispiel-Screenshot für KI-Assistent."""

    description: str = Field(default="", max_length=4000)
    label_hint: str | None = Field(default=None, max_length=120)
    attachments: list[WorkflowMediaAttachment] = Field(default_factory=list)

    @field_validator("attachments")
    @classmethod
    def validate_suggest_attachments(
        cls, value: list[WorkflowMediaAttachment]
    ) -> list[WorkflowMediaAttachment]:
        if len(value) > MAX_ATTACHMENTS_PER_REQUEST:
            msg = f"At most {MAX_ATTACHMENTS_PER_REQUEST} attachments per suggest"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def require_description_or_attachment(self) -> TenantWorkflowSuggestRequest:
        if self.attachments:
            return self
        if len(self.description.strip()) < 10:
            msg = (
                "description must be at least 10 characters when no "
                "attachments are provided"
            )
            raise ValueError(msg)
        return self


class TenantWorkflowSuggestResponse(BaseModel):
    """KI-Vorschlag — noch nicht gespeichert."""

    label: str
    slug: str
    description: str
    search_hints: str
    importance: WorkflowImportance
    required_fields: list[str]
    optional_fields: list[str]
    extraction_schema: dict[str, Any]
    classify_prompt: str
    extract_prompt: str
    multimodal_prompt: str = ""
    match_rules: WorkflowMatchRulesSchema
    test_emails: list[WorkflowTestEmailSchema]
    llm_provider: WorkflowLlmProvider = "openai"
    supports_multimodal: bool = False


class TenantWorkflowPreviewRequest(BaseModel):
    subject: str = "Test-Betreff"
    body: str = "Test-Inhalt der E-Mail."
    attachments: list[WorkflowMediaAttachment] = Field(default_factory=list)

    @field_validator("attachments")
    @classmethod
    def validate_attachments(
        cls, value: list[WorkflowMediaAttachment]
    ) -> list[WorkflowMediaAttachment]:
        if len(value) > MAX_ATTACHMENTS_PER_REQUEST:
            msg = f"At most {MAX_ATTACHMENTS_PER_REQUEST} attachments per preview"
            raise ValueError(msg)
        return value


class TenantWorkflowPreviewResponse(BaseModel):
    success: bool
    result: str | None = None
    error: str | None = None
    model: str
    notice: str | None = None


class GeminiStatusResponse(BaseModel):
    configured: bool
    available: bool
    model: str
    ocr_available: bool = False


class TenantWorkflowTestCaseResult(BaseModel):
    subject: str
    success: bool
    result: str | None = None
    error: str | None = None


class TenantWorkflowRunTestsResponse(BaseModel):
    workflow_id: str
    total: int
    passed: int
    results: list[TenantWorkflowTestCaseResult]
