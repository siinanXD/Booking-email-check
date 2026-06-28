"""Übersetzt Antwortentwürfe für den DE/EN-Umschalter im Review."""

from __future__ import annotations

from backend.core.config.app_context import AppContext

_LANG_LABEL = {"de": "Deutsch", "en": "Englisch"}


def translate_draft(
    ctx: AppContext,
    account_id: str,
    correlation_id: str,
    target_language: str,
    draft_body: str | None = None,
) -> str:
    """Übersetzt den Entwurf in die Zielsprache; gibt Original bei Fehlern zurück."""
    record = ctx.review_repo.get(correlation_id, account_id=account_id)
    body = (draft_body if draft_body is not None else "").strip()
    if not body and record is not None:
        body = record.draft_body.strip()
    if not body:
        return ""
    if ctx.llm is None:
        return body
    label = _LANG_LABEL.get(target_language, "Deutsch")
    prompt = (
        f"Übersetze die folgende Antwort an einen Hotelgast professionell und "
        f"höflich nach {label}. Gib ausschließlich die Übersetzung zurück, ohne "
        f"Anführungszeichen oder Erklärungen.\n\n{body}"
    )
    try:
        completion = ctx.llm.complete(prompt, ctx.settings.openai_model_draft)
    except Exception:  # noqa: BLE001 - Übersetzung darf nie 500 werfen
        return body
    return completion.text.strip() or body
