"""In-Process-Stresstests für den Ingestion-Pfad.

Führt N Mails sequenziell und parallel durch die Ingestion-Pipeline
(MockLLM + mongomock) und misst Durchsatz und Fehlerrate. Läuft in CI
ohne externe Dienste.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any

import pytest

from backend.ai.services.ingestion import IngestionService
from backend.ai.services.triage import TriageService
from backend.core.models.email import IncomingEmail
from backend.infrastructure.repositories.email_repository import EmailRepository


def _make_email(index: int, *, platform: str = "airbnb") -> IncomingEmail:
    return IncomingEmail(
        message_id=f"stress-{index:05d}@test.local",
        from_address=f"guest{index}@{platform}.com",
        subject=f"Stornierung AB{100 + index}",
        body_text=f"Bitte stornieren Sie die Reservierung AB{100 + index}.",
        received_at=datetime.now(UTC),
        platform=platform,
    )


@pytest.fixture
def stress_ingestion_service(mock_db: Any) -> IngestionService:
    """Ingestion mit Regel-Triage (kein LLM-Call)."""
    return IngestionService(
        EmailRepository(mock_db),
        TriageService(triage_llm_enabled=False),
    )


# ---------------------------------------------------------------------------
# Sequentiell
# ---------------------------------------------------------------------------


def test_sequential_ingestion_50_emails(
    stress_ingestion_service: IngestionService,
    email_repo: EmailRepository,
) -> None:
    """50 Booking-Mails sequentiell – kein Fehler, alle gespeichert."""
    n = 50
    errors = 0
    for i in range(n):
        try:
            result = stress_ingestion_service.ingest(_make_email(i))
            assert result.email is not None
        except Exception:  # noqa: BLE001
            errors += 1

    assert errors == 0
    total = email_repo.count_received_since("2000-01-01T00:00:00")
    assert total >= n


def test_sequential_ingestion_throughput(
    stress_ingestion_service: IngestionService,
) -> None:
    """50 Mails müssen in unter 5 Sekunden ingested werden (MockLLM)."""
    n = 50
    start = time.monotonic()
    for i in range(1000, 1000 + n):
        stress_ingestion_service.ingest(_make_email(i))
    elapsed = time.monotonic() - start
    assert elapsed < 5.0, f"Throughput zu langsam: {n} Mails in {elapsed:.1f}s"


# ---------------------------------------------------------------------------
# Parallel
# ---------------------------------------------------------------------------


def test_parallel_ingestion_no_errors(mock_db: Any) -> None:
    """20 Mails gleichzeitig von 4 Threads – keine Race Conditions, kein Fehler."""
    n_per_thread = 5
    n_threads = 4
    errors: list[Exception] = []

    def _ingest_batch(thread_idx: int) -> int:
        repo = EmailRepository(mock_db)
        svc = IngestionService(repo, TriageService(triage_llm_enabled=False))
        count = 0
        for i in range(n_per_thread):
            msg_index = thread_idx * 1000 + i
            result = svc.ingest(_make_email(msg_index + 2000))
            if result.email is not None:
                count += 1
        return count

    with ThreadPoolExecutor(max_workers=n_threads) as pool:
        futures = [pool.submit(_ingest_batch, t) for t in range(n_threads)]
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

    assert errors == [], f"Fehler bei Parallel-Ingestion: {errors}"


# ---------------------------------------------------------------------------
# Deduplizierung unter Last
# ---------------------------------------------------------------------------


def test_deduplication_under_concurrent_load(mock_db: Any) -> None:
    """Gleiche message_id von 3 Threads → nur 1 Dokument in der DB."""
    email = _make_email(9999)
    results: list[bool] = []

    def _try_ingest() -> None:
        repo = EmailRepository(mock_db)
        svc = IngestionService(repo, TriageService(triage_llm_enabled=False))
        r = svc.ingest(email)
        results.append(r.email is not None)

    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = [pool.submit(_try_ingest) for _ in range(3)]
        for f in futs:
            f.result()

    repo = EmailRepository(mock_db)
    stored = repo.get_by_message_id(email.message_id)
    assert stored is not None, "Mail wurde gar nicht gespeichert"
    # Kein Duplikat (upsert_by_message_id ist idempotent)
    total, _ = repo.list_filtered(search=email.message_id)
    # Suche per search-Param (correlation_id exact match)
    by_corr = repo.list_by_correlation_id(email.correlation_id)
    assert len(by_corr) == 1, f"Duplikate gefunden: {len(by_corr)}"


# ---------------------------------------------------------------------------
# Verschiedene Plattformen
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("platform", ["airbnb", "booking", "expedia", "vrbo", "direct"])
def test_ingestion_per_platform(
    stress_ingestion_service: IngestionService,
    platform: str,
) -> None:
    """Ingestion funktioniert für alle unterstützten Plattformen."""
    email = _make_email(5000, platform=platform)
    result = stress_ingestion_service.ingest(email)
    assert result.email is not None
    assert result.email.platform == platform
