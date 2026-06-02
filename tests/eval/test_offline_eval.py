"""Offline-Evals: Mock (CI-Verdrahtung) oder Live (Extraktionsqualität)."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import pytest

from models.email import StoredEmail
from schemas.booking.taxonomy import BookingIntent
from services.classification import ClassificationService, OpenAIClient
from services.extraction import ExtractionService
from services.validation import ValidationService
from tests.eval.compare import run_extraction_eval
from tests.mocks import MockLLM


def _eval_mode() -> str:
    return os.environ.get("EVAL_LLM_MODE", "mock").strip().lower()


def _build_llm() -> MockLLM | OpenAIClient:
    mode = _eval_mode()
    if mode == "live":
        from config.settings import get_settings

        settings = get_settings()
        return OpenAIClient(settings.openai_api_key)
    if mode != "mock":
        msg = f"Unknown EVAL_LLM_MODE={mode!r}; use mock or live"
        raise ValueError(msg)
    return MockLLM()


@pytest.fixture
def eval_cases() -> list[dict[str, object]]:
    path = Path(__file__).parent / "cases.json"
    data: list[dict[str, object]] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _email_from_case(case: dict[str, object]) -> StoredEmail:
    return StoredEmail(
        message_id=str(case["message_id"]),
        from_address=str(case["from_address"]),
        subject=str(case["subject"]),
        body_text=str(case["body_text"]),
        received_at=datetime.fromisoformat(
            str(case["received_at"]).replace("Z", "+00:00")
        ),
        platform=case.get("platform"),  # type: ignore[arg-type]
    )


def test_eval_classification_intent(
    eval_cases: list[dict[str, object]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Intent-Slug pro Fall (Mock oder Live)."""
    mode = _eval_mode()
    if mode == "live":
        pytest.importorskip("openai")
    llm = _build_llm()
    svc = ClassificationService(llm, "gpt-4o-mini")
    passed = 0
    for case in eval_cases:
        intent = svc.classify(_email_from_case(case))
        if intent == BookingIntent(str(case["expected_intent"])):
            passed += 1
    rate = passed / len(eval_cases) if eval_cases else 1.0
    note = "wiring_regression" if mode == "mock" else "classification_quality_live"
    line = (
        f"OFFLINE_EVAL classify mode={mode} note={note} "
        f"hit_rate={rate:.2f} ({passed}/{len(eval_cases)} cases)"
    )
    print(line)
    assert line in capsys.readouterr().out
    if mode == "mock":
        min_rate = float(os.environ.get("EVAL_MIN_CASE_RATE", "1.0"))
        assert rate >= min_rate


def test_eval_extraction_field_accuracy(
    eval_cases: list[dict[str, object]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Feld-für-Feld gegen expected_extraction; Mock misst Verdrahtung."""
    mode = _eval_mode()
    if mode == "live":
        pytest.importorskip("openai")
    llm = _build_llm()
    extract_svc = ExtractionService(llm, "gpt-4o-mini")

    def extract_fn(email: StoredEmail, intent: BookingIntent | None = None):
        return extract_svc.extract(email, intent=intent)

    report = run_extraction_eval(eval_cases, extract_fn)
    line = report.summary_line(mode)
    print(line)
    assert line in capsys.readouterr().out
    if mode == "mock":
        min_rate = float(os.environ.get("EVAL_MIN_CASE_RATE", "1.0"))
        assert report.case_hit_rate >= min_rate
        assert report.field_accuracy >= min_rate


def test_eval_validation_when_expected(
    eval_cases: list[dict[str, object]],
) -> None:
    """Optional expect_validation_valid in cases.json."""
    validation = ValidationService()
    llm = _build_llm()
    extract_svc = ExtractionService(llm, "gpt-4o-mini")
    for case in eval_cases:
        if "expect_validation_valid" not in case:
            continue
        email = _email_from_case(case)
        intent = BookingIntent(str(case["expected_intent"]))
        ext = extract_svc.extract(email, intent=intent)
        result = validation.validate(ext)
        assert result.valid is case["expect_validation_valid"]
