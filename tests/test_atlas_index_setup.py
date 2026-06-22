"""Atlas-Vector-Index-Definition."""

from __future__ import annotations

from typing import Any, cast

from backend.infrastructure.repositories.embedding_repository import (
    build_vector_index_definition,
)


def test_index_definition_has_vector_and_account_filter() -> None:
    """Index muss embedding-Vektor UND account_id-Filter deklarieren.

    Ohne den account_id-Filter scheitert die mandantengefilterte
    $vectorSearch-Abfrage und RAG liefert nie similar_cases.
    """
    fields = cast(list[dict[str, Any]], build_vector_index_definition()["fields"])
    by_path = {f["path"]: f for f in fields}
    assert by_path["embedding"]["type"] == "vector"
    assert by_path["embedding"]["numDimensions"] == 1536
    assert by_path["embedding"]["similarity"] == "cosine"
    assert by_path["account_id"]["type"] == "filter"
