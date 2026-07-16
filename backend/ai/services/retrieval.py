"""Metadaten-Retrieval (Mongo, kein Vector im Schritt 3)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import uuid4

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.services.entity_resolution import EntityResolutionService
from backend.ai.services.reranking import RerankService
from backend.ai.services.semantic_chunking import (
    build_context_prefix,
    preprocess_mail_body,
)
from backend.ai.services.similarity_search import SimilaritySearchService
from backend.core.models.email import StoredEmail
from backend.core.models.entities import Guest, Reservation
from backend.infrastructure.observability.alerts import AlertService
from backend.infrastructure.repositories.email_repository import EmailRepository
from backend.infrastructure.repositories.entity_repository import EntityRepository
from backend.infrastructure.repositories.platform_llm_config_repository import (
    PlatformLlmConfigRepository,
)
from backend.infrastructure.repositories.property_repository import PropertyRepository

logger = logging.getLogger(__name__)


@dataclass
class RetrievalHits:
    """Kontext für Antwortgenerierung."""

    guest: Guest | None = None
    reservations: list[Reservation] = field(default_factory=list)
    thread_emails: list[StoredEmail] | None = None
    similar_cases: list[dict[str, object]] = field(default_factory=list)
    # Hausregeln der erkannten Unterkunft — einzige erlaubte Wissensquelle für
    # inhaltliche Gastfragen (Parken, Check-in, WLAN …).
    house_rules: str | None = None


class RetrievalService:
    """Strukturierte Abfragen über Metadaten."""

    def __init__(
        self,
        entity_repo: EntityRepository,
        email_repo: EmailRepository,
        similarity: SimilaritySearchService | None = None,
        *,
        entity_resolution: EntityResolutionService | None = None,
        alerts: AlertService | None = None,
        llm_config_repo: PlatformLlmConfigRepository | None = None,
        reranker: RerankService | None = None,
        property_repo: PropertyRepository | None = None,
    ) -> None:
        """Initialize the instance with its dependencies."""
        self._entities = entity_repo
        self._emails = email_repo
        self._similarity = similarity
        self._entity_resolution = entity_resolution or EntityResolutionService(
            entity_repo
        )
        self._alerts = alerts
        self._llm_config_repo = llm_config_repo
        self._reranker = reranker
        self._properties = property_repo

    def retrieve(
        self,
        email: StoredEmail,
        extraction: BookingExtraction | None = None,
        include_similar: bool = False,
        max_reservations: int = 20,
    ) -> RetrievalHits:
        """Lädt Gast, Reservierungen und Thread-Kontext."""
        account_id = email.account_id
        guest: Guest | None = None
        reservations: list[Reservation] = []

        if extraction is not None:
            guest, _confidence = self._entity_resolution.resolve_guest(
                extraction,
                email.from_address,
                account_id=account_id,
            )
            if guest is None and self._should_create_guest(extraction, email):
                guest = Guest(
                    guest_id=str(uuid4()),
                    name=extraction.guest_name,
                    email=(extraction.email or email.from_address or None),
                    phone=extraction.phone,
                    platform=extraction.platform,
                    account_id=account_id,
                )
                self._entities.upsert_guest(guest, account_id=account_id)

            if guest is not None:
                reservations = self._entities.find_reservations_by_guest_id(
                    guest.guest_id,
                    account_id=account_id,
                )

        if extraction and extraction.booking_number:
            by_number = self._entities.find_reservation_by_booking_number(
                extraction.booking_number,
                account_id=account_id,
            )
            if by_number and by_number not in reservations:
                reservations.append(by_number)

        thread_ids = email.thread_ids()
        thread_emails: list[StoredEmail] = []
        for tid in thread_ids:
            found = self._emails.get_by_message_id(tid, account_id=account_id)
            if found:
                thread_emails.append(found)

        if not reservations:
            reservations = self._entities.find_reservations_by_correlation_id(
                email.correlation_id,
                account_id=account_id,
            )

        reservations = self._cap_reservations(
            reservations,
            max_reservations,
            email.correlation_id,
        )

        if extraction and extraction.booking_number:
            booking_found = any(
                r.booking_number == extraction.booking_number for r in reservations
            )
            if not booking_found and self._alerts is not None:
                self._alerts.check_retrieval_empty(
                    email.correlation_id,
                    f"booking_number_not_found:{extraction.booking_number}",
                )

        similar: list[dict[str, object]] = []
        if include_similar and self._similarity is not None:
            top_k = 3
            if self._llm_config_repo is not None:
                top_k = self._llm_config_repo.get_or_default().similarity_top_k
            query_text = self._similarity_query(email, extraction)
            if query_text:
                fetch_limit = (
                    self._reranker.candidate_limit(top_k)
                    if self._reranker is not None
                    else top_k
                )
                candidates = self._similarity.find_similar_cases(
                    query_text,
                    limit=fetch_limit,
                    account_id=account_id,
                )
                if self._reranker is not None:
                    similar = self._reranker.rerank(query_text, candidates, top_k)
                else:
                    similar = candidates[:top_k]

        return RetrievalHits(
            guest=guest,
            reservations=reservations,
            thread_emails=thread_emails or None,
            similar_cases=similar,
            house_rules=self._house_rules(extraction, account_id),
        )

    def _house_rules(
        self,
        extraction: BookingExtraction | None,
        account_id: str | None,
    ) -> str | None:
        """Hausregeln der erkannten Unterkunft (exakter Name, wie im Katalog).

        Kein Fuzzy-Match: der property_name ist zu diesem Zeitpunkt bereits über
        ``match_known_property_name`` auf den Katalog gezogen. Trifft er nicht,
        gibt es lieber keine Regeln als die einer fremden Wohnung.
        """
        if self._properties is None or extraction is None or not account_id:
            return None
        name = (extraction.property_name or "").strip()
        if not name:
            return None
        for prop in self._properties.list_all(account_id=account_id):
            if prop.name.strip().lower() == name.lower():
                rules = (prop.house_rules or "").strip()
                return rules or None
        return None

    @staticmethod
    def _similarity_query(
        email: StoredEmail,
        extraction: BookingExtraction | None,
    ) -> str:
        """Such-Query symmetrisch zum Index: Kontext-Prefix + zitatbereinigter Body.

        Spiegelt die Struktur der indexierten Chunks (``build_context_prefix`` +
        ``preprocess_mail_body``), damit Query- und Dokument-Vektorraum
        zusammenpassen. Rohe Zitat-Historie/Signaturen verschlechtern sonst das
        Query-Embedding.
        """
        intent = extraction.intent.value if extraction and extraction.intent else None
        prefix = build_context_prefix(
            subject=email.subject,
            intent=intent,
            property_name=extraction.property_name if extraction else None,
            booking_number=extraction.booking_number if extraction else None,
        )
        body = preprocess_mail_body(email.body_text or "", email.body_html)
        return f"{prefix}{body}".strip()

    @staticmethod
    def _should_create_guest(
        extraction: BookingExtraction,
        email: StoredEmail,
    ) -> bool:
        return bool(extraction.guest_name or extraction.email or email.from_address)

    @staticmethod
    def _cap_reservations(
        reservations: list[Reservation],
        max_reservations: int,
        correlation_id: str,
    ) -> list[Reservation]:
        if len(reservations) <= max_reservations:
            return reservations
        logger.warning(
            "retrieval_truncated",
            extra={
                "correlation_id": correlation_id,
                "total": len(reservations),
                "max_reservations": max_reservations,
            },
        )
        return reservations[:max_reservations]
