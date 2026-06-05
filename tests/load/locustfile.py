"""Locust-Lasttest gegen einen laufenden Flask-Server.

Starten:
    pip install locust
    locust -f tests/load/locustfile.py --host=http://localhost:5000

Szenarien:
  - ReviewUser: Login → Review-Queue lesen → Approve/Reject
  - ReadOnlyUser: Login → Dashboard → E-Mail-Liste
"""

from __future__ import annotations

import random

from locust import HttpUser, between, task


class _AuthMixin:
    """Gemeinsame Login-Logik."""

    client: object  # Locust injects this

    _token: str | None = None

    def on_start(self) -> None:
        resp = self.client.post(  # type: ignore[attr-defined]
            "/api/auth/login",
            json={
                "email": "admin@example.com",
                "password": "change-me",
            },
        )
        if resp.status_code == 200:
            self._token = resp.json().get("access_token")

    @property
    def _headers(self) -> dict[str, str]:
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}


class ReadOnlyUser(_AuthMixin, HttpUser):
    """Simuliert einen Nutzer der nur liest."""

    wait_time = between(0.5, 2)

    @task(3)
    def dashboard(self) -> None:
        self.client.get("/api/dashboard/stats", headers=self._headers)

    @task(5)
    def list_emails(self) -> None:
        page = random.randint(1, 3)
        self.client.get(
            f"/api/emails/?page={page}&limit=20",
            headers=self._headers,
        )

    @task(2)
    def list_emails_by_intent(self) -> None:
        intent = random.choice(
            ["new_booking", "cancellation", "guest_inquiry", "change", "other"]
        )
        self.client.get(
            f"/api/emails/?intent={intent}",
            headers=self._headers,
        )

    @task(1)
    def health_check(self) -> None:
        self.client.get("/health")


class ReviewUser(_AuthMixin, HttpUser):
    """Simuliert einen Reviewer der die Queue abarbeitet."""

    wait_time = between(1, 4)

    @task(5)
    def list_pending(self) -> None:
        self.client.get("/api/review/pending", headers=self._headers)

    @task(2)
    def list_completed(self) -> None:
        self.client.get("/api/review/completed", headers=self._headers)

    @task(1)
    def approve_random(self) -> None:
        """Nimmt ein pending Item und approvet es (sofern vorhanden)."""
        resp = self.client.get(
            "/api/review/pending?limit=5",
            headers=self._headers,
        )
        if resp.status_code != 200:
            return
        items = resp.json().get("items", [])
        if not items:
            return
        item = random.choice(items)
        self.client.post(
            "/api/review/approve",
            json={
                "correlation_id": item["correlation_id"],
                "approved_body": item.get("draft_body", "Genehmigt."),
            },
            headers=self._headers,
        )
