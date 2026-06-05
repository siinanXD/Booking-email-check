"""Mandanten-Workflows: CRUD, KI-Vorschläge, Preview (Phase A — Sandbox)."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.ai.services.gemini_setup import gemini_available, gemini_configured
from backend.ai.services.ocr_service import ocr_available
from backend.ai.services.tenant_workflow_gemini import gemini_ready
from backend.ai.services.tenant_workflow_suggest_gemini import (
    SuggestRequiresGeminiError,
    mock_suggest_from_example,
    run_gemini_suggest_from_example,
)
from backend.api.schemas.tenant_workflows import (
    GeminiStatusResponse,
    TenantWorkflowCreateRequest,
    TenantWorkflowListResponse,
    TenantWorkflowNavItem,
    TenantWorkflowNavResponse,
    TenantWorkflowPreviewRequest,
    TenantWorkflowPreviewResponse,
    TenantWorkflowResponse,
    TenantWorkflowRunTestsResponse,
    TenantWorkflowSuggestRequest,
    TenantWorkflowSuggestResponse,
    TenantWorkflowTestCaseResult,
    TenantWorkflowUpdateRequest,
)
from backend.api.services.tenant_workflow_internal import (
    _definition_changed,
    _record_from_request,
    _resolve_slug,
    _run_extract_preview,
    _to_response,
    _to_summary,
)
from backend.api.services.tenant_workflow_suggest_fallback import (
    _llm_suggest,
    _mock_suggest,
)
from backend.api.services.tenant_workflow_suggest_ocr import run_ocr_suggest
from backend.core.config.factory import AppContext
from backend.core.config.settings import Settings


def gemini_status(settings: Settings, ctx: AppContext) -> GeminiStatusResponse:
    """Status für UI (kein API-Key-Leak)."""
    return GeminiStatusResponse(
        configured=gemini_configured(settings),
        available=gemini_available(settings),
        model=settings.gemini_model_extract,
        ocr_available=ocr_available(),
    )


def list_workflows(ctx: AppContext, account_id: str) -> TenantWorkflowListResponse:
    records = ctx.tenant_workflow_repo.list_for_account(account_id)
    return TenantWorkflowListResponse(
        items=[_to_summary(record) for record in records],
    )


def list_nav_workflows(ctx: AppContext, account_id: str) -> TenantWorkflowNavResponse:
    """Live-Workflows für Mandanten-Navigation (keine Sandbox)."""
    records = ctx.tenant_workflow_repo.list_live(account_id)
    return TenantWorkflowNavResponse(
        items=[
            TenantWorkflowNavItem(
                id=record.id,
                slug=record.slug,
                label=record.label,
                description=record.description,
            )
            for record in records
        ],
    )


def get_workflow(
    ctx: AppContext,
    account_id: str,
    workflow_id: str,
) -> TenantWorkflowResponse | None:
    record = ctx.tenant_workflow_repo.get(account_id, workflow_id)
    if record is None:
        return None
    return _to_response(record)


def create_workflow(
    ctx: AppContext,
    account_id: str,
    body: TenantWorkflowCreateRequest,
    *,
    user_id: str | None,
) -> TenantWorkflowResponse:
    slug = _resolve_slug(body.slug, body.label)
    if body.enabled and not body.sandbox_only:
        msg = (
            "Workflow kann erst nach bestandener Test-Suite live aktiviert werden. "
            "Bitte zunächst speichern, Test-Suite ausführen, dann aktivieren."
        )
        raise ValueError(msg)
    record = _record_from_request(body, account_id=account_id, slug=slug)
    saved = ctx.tenant_workflow_repo.create(record, created_by_user_id=user_id)
    return _to_response(saved)


def update_workflow(
    ctx: AppContext,
    account_id: str,
    workflow_id: str,
    body: TenantWorkflowUpdateRequest,
    *,
    user_id: str | None,
) -> TenantWorkflowResponse | None:
    existing = ctx.tenant_workflow_repo.get(account_id, workflow_id)
    if existing is None:
        return None
    slug = _resolve_slug(body.slug, body.label, fallback=existing.slug)
    record = _record_from_request(
        body,
        account_id=account_id,
        slug=slug,
        workflow_id=existing.id,
    )
    if _definition_changed(existing, body):
        record.last_test_passed_at = None
        record.last_test_passed_count = 0
        record.last_test_passed_total = 0
    else:
        record.last_test_passed_at = existing.last_test_passed_at
        record.last_test_passed_count = existing.last_test_passed_count
        record.last_test_passed_total = existing.last_test_passed_total

    if body.enabled and not body.sandbox_only:
        if (
            record.last_test_passed_at is None
            or record.last_test_passed_total <= 0
            or record.last_test_passed_count != record.last_test_passed_total
        ):
            msg = (
                "Alle Test-Mails müssen bestehen, bevor der Workflow live "
                "aktiviert werden kann. Bitte Test-Suite ausführen."
            )
            raise ValueError(msg)

    saved = ctx.tenant_workflow_repo.update(record, updated_by_user_id=user_id)
    return _to_response(saved)


def delete_workflow(ctx: AppContext, account_id: str, workflow_id: str) -> bool:
    return ctx.tenant_workflow_repo.delete(account_id, workflow_id)


def suggest_workflow(
    ctx: AppContext,
    settings: Settings,
    body: TenantWorkflowSuggestRequest,
) -> TenantWorkflowSuggestResponse:
    if body.attachments:
        if settings.llm_mode.strip().lower() == "mock":
            return mock_suggest_from_example(body)
        if gemini_ready(settings, ctx.gemini_client):
            assert ctx.gemini_client is not None
            return run_gemini_suggest_from_example(
                gemini=ctx.gemini_client,
                settings=settings,
                body=body,
            )
        if ocr_available():
            return run_ocr_suggest(ctx, settings, body)
        raise SuggestRequiresGeminiError(
            "Für Vorschläge aus Bildern wird GEMINI_API_KEY oder PaddleOCR benötigt. "
            "Alternativ nur Text-Beschreibung nutzen."
        )
    if settings.llm_mode.strip().lower() == "mock":
        return _mock_suggest(body)
    return _llm_suggest(ctx, settings, body)


def preview_workflow(
    ctx: AppContext,
    settings: Settings,
    account_id: str,
    workflow_id: str,
    body: TenantWorkflowPreviewRequest,
) -> TenantWorkflowPreviewResponse | None:
    record = ctx.tenant_workflow_repo.get(account_id, workflow_id)
    if record is None:
        return None
    return _run_extract_preview(
        ctx,
        settings,
        record,
        body.subject,
        body.body,
        body.attachments,
    )


def run_workflow_tests(
    ctx: AppContext,
    settings: Settings,
    account_id: str,
    workflow_id: str,
) -> TenantWorkflowRunTestsResponse | None:
    record = ctx.tenant_workflow_repo.get(account_id, workflow_id)
    if record is None:
        return None
    results: list[TenantWorkflowTestCaseResult] = []
    passed = 0
    for test in record.test_emails:
        preview = _run_extract_preview(
            ctx,
            settings,
            record,
            test.subject,
            test.body,
            test.attachments,
        )
        ok = preview.success
        if ok:
            passed += 1
        results.append(
            TenantWorkflowTestCaseResult(
                subject=test.subject,
                success=ok,
                result=preview.result,
                error=preview.error,
            )
        )
    total = len(results)
    record.last_test_passed_at = (
        datetime.now(UTC) if passed == total and total > 0 else None
    )
    record.last_test_passed_count = passed if passed == total and total > 0 else 0
    record.last_test_passed_total = total if passed == total and total > 0 else 0
    ctx.tenant_workflow_repo.update(record)

    return TenantWorkflowRunTestsResponse(
        workflow_id=workflow_id,
        total=len(results),
        passed=passed,
        results=results,
    )
