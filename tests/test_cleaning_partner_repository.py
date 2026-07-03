"""Tests für die Putzpartner-Zuordnung (case-/whitespace-insensitiv)."""

from __future__ import annotations

import pytest

from backend.features.cleaning.models import CleaningPartner
from backend.infrastructure.repositories.cleaning_partner_repository import (
    CleaningPartnerRepository,
)
from backend.infrastructure.repositories.mongo import Db

ACCOUNT = "acc-1"


@pytest.fixture
def repo(mock_db: Db) -> CleaningPartnerRepository:
    """Execute the operation."""
    return CleaningPartnerRepository(mock_db)


def _partner(names: list[str]) -> CleaningPartner:
    return CleaningPartner(
        partner_id="p1",
        account_id=ACCOUNT,
        name="Putz GmbH",
        phone="+491701234567",
        property_names=names,
    )


@pytest.mark.parametrize(
    "query",
    ["Villa A", "villa a", "VILLA A", "  Villa A  "],
)
def test_find_for_property_case_and_whitespace_insensitive(
    repo: CleaningPartnerRepository, query: str
) -> None:
    repo.upsert(_partner(["Villa A"]), account_id=ACCOUNT)
    found = repo.find_for_property(query, account_id=ACCOUNT)
    assert [p.partner_id for p in found] == ["p1"]


def test_find_for_property_legacy_doc_without_lower_column(
    repo: CleaningPartnerRepository, mock_db: Db
) -> None:
    """Altbestand ohne property_names_lower muss über den Regex-Fallback greifen."""
    mock_db[CleaningPartnerRepository.COLLECTION].insert_one(
        {
            "_id": "legacy",
            "account_id": ACCOUNT,
            "name": "Alt Partner",
            "phone": "+491700000000",
            "property_names": ["Villa A"],
            "active": True,
        }
    )
    found = repo.find_for_property("villa a", account_id=ACCOUNT)
    assert [p.partner_id for p in found] == ["legacy"]


def test_find_for_property_no_false_positive(
    repo: CleaningPartnerRepository,
) -> None:
    repo.upsert(_partner(["Villa A"]), account_id=ACCOUNT)
    assert repo.find_for_property("Villa B", account_id=ACCOUNT) == []
