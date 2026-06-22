"""Reranking-Tests (zweistufiges Retrieval)."""

from __future__ import annotations

from typing import cast

from backend.ai.services.llm_types import LLMCompletion
from backend.ai.services.reranking import RerankService


class _StubLLM:
    """LLM-Stub mit fester Antwort, zählt Aufrufe."""

    def __init__(self, text: str) -> None:
        self._text = text
        self.calls = 0

    def complete(self, prompt, model, *, temperature=None):  # noqa: ANN001
        self.calls += 1
        return LLMCompletion(text=self._text)


def _cands(n: int) -> list[dict[str, object]]:
    return [{"correlation_id": f"c{i}", "text": f"Fall {i}"} for i in range(n)]


def test_rerank_reorders_by_llm_output() -> None:
    llm = _StubLLM("2,0,1")
    out = RerankService(llm, "m", enabled=True).rerank("query", _cands(3), top_k=3)
    assert [c["correlation_id"] for c in out] == ["c2", "c0", "c1"]
    scores = [cast(float, c["rerank_score"]) for c in out]
    assert scores[0] > scores[1] > scores[2]


def test_rerank_respects_top_k() -> None:
    llm = _StubLLM("3,2,1,0")
    out = RerankService(llm, "m", enabled=True).rerank("q", _cands(4), top_k=2)
    assert [c["correlation_id"] for c in out] == ["c3", "c2"]


def test_rerank_disabled_returns_vector_order_without_llm() -> None:
    llm = _StubLLM("2,0,1")
    out = RerankService(llm, "m", enabled=False).rerank("q", _cands(3), top_k=2)
    assert [c["correlation_id"] for c in out] == ["c0", "c1"]
    assert llm.calls == 0


def test_rerank_appends_unmentioned_candidates() -> None:
    llm = _StubLLM("1")  # LLM nennt nur einen Fall
    out = RerankService(llm, "m", enabled=True).rerank("q", _cands(3), top_k=3)
    assert [c["correlation_id"] for c in out] == ["c1", "c0", "c2"]


def test_rerank_fallback_on_llm_error() -> None:
    class _FailLLM:
        def complete(self, prompt, model, *, temperature=None):  # noqa: ANN001
            raise TimeoutError("slow")

    out = RerankService(_FailLLM(), "m", enabled=True).rerank("q", _cands(3), top_k=2)
    assert [c["correlation_id"] for c in out] == ["c0", "c1"]


def test_candidate_limit_scales_only_when_enabled() -> None:
    llm = _StubLLM("0")
    on = RerankService(llm, "m", enabled=True, candidate_multiplier=4)
    off = RerankService(llm, "m", enabled=False)
    assert on.candidate_limit(3) == 12
    assert off.candidate_limit(3) == 3
