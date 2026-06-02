"""Prüft API-Endpunkte und Listen-Zähler (Dev)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _bootstrap import require_project_venv

require_project_venv()


def main() -> int:
    from config.settings import get_settings

    settings = get_settings()
    if not settings.admin_password:
        print("FEHLER: ADMIN_PASSWORD nicht gesetzt")
        return 1

    try:
        import urllib.error
        import urllib.request

        base = "http://127.0.0.1:5000"

        def req(
            method: str,
            path: str,
            body: dict[str, Any] | None = None,
            token: str | None = None,
        ) -> tuple[int, Any]:
            data = None
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            if body is not None:
                data = json.dumps(body).encode("utf-8")
            r = urllib.request.Request(
                f"{base}{path}",
                data=data,
                headers=headers,
                method=method,
            )
            with urllib.request.urlopen(r, timeout=30) as resp:
                return resp.status, json.loads(resp.read().decode())

        status, _ = req("GET", "/health")
        print(f"health: {status}")
        if status != 200:
            return 1

        status, tokens = req(
            "POST",
            "/api/auth/login",
            {"email": settings.admin_email, "password": settings.admin_password},
        )
        if status != 200:
            print(f"login failed: {status}")
            return 1
        token = tokens["access_token"]
        print(f"login: ok ({settings.admin_email})")

        checks: list[tuple[str, str]] = [
            ("dashboard", "/api/dashboard/stats"),
            ("bookings", "/api/bookings/?page=1&limit=5"),
            (
                "cancellations",
                "/api/emails/?intent=cancellation&booking_related=true&limit=5",
            ),
            ("changes", "/api/emails/?intent=change&booking_related=true&limit=5"),
            (
                "messages",
                "/api/emails/?intent=guest_inquiry&booking_related=true&limit=5",
            ),
            ("review", "/api/review/pending?limit=10"),
            ("costs", "/api/costs/?from_date=2026-01-01&group_by=day"),
        ]
        errors = 0
        for name, path in checks:
            try:
                status, data = req("GET", path, token=token)
                if status != 200:
                    print(f"  {name}: HTTP {status} FEHLER")
                    errors += 1
                    continue
                if name == "dashboard":
                    print(
                        f"  dashboard: eingegangen_heute={data.get('total_emails_today')} "
                        f"buchungen_heute={data.get('new_bookings_today')} "
                        f"stornos_heute={data.get('cancellations_today')} "
                        f"review_pending={data.get('pending_review')} "
                        f"kosten_heute=${data.get('cost_today_usd')}"
                    )
                elif name == "costs":
                    series = data.get("series") or []
                    print(
                        f"  costs: total_usd={data.get('total_usd')} "
                        f"tage={len(series)} mails_metrik={sum(p.get('mail_count', 0) for p in series)}"
                    )
                elif name == "review":
                    items = data.get("items") or []
                    drafts = sum(
                        1 for i in items if (i.get("draft_body") or "").strip()
                    )
                    print(f"  review: total={data.get('total')} mit_entwurf={drafts}")
                    if items:
                        print(f"    beispiel: {items[0].get('subject', '')[:40]}")
                else:
                    total = data.get("total", "?")
                    items = data.get("items") or []
                    sample = ""
                    if items:
                        sample = f" | {items[0].get('subject', '')[:35]}"
                    print(f"  {name}: total={total}{sample}")
            except urllib.error.URLError as exc:
                print(f"  {name}: nicht erreichbar ({exc})")
                errors += 1

        from config.factory import build_app_context
        from models.email import StoredEmail
        from services.booking_relevance import is_marketing_noise

        ctx = build_app_context(settings)
        comigo_in_cancel = 0
        for doc in ctx.email_repo._col.find().limit(500):
            email = StoredEmail.from_mongo(doc)
            if not is_marketing_noise(email):
                continue
            ext = ctx.extraction_repo.get_by_correlation_id(email.correlation_id)
            if ext and ext.intent and ext.intent.value == "cancellation":
                comigo_in_cancel += 1
        print(
            f"  noise_als_storno_in_db: {comigo_in_cancel} (soll 0 nach fix_noise_intents)"
        )
        print(f"  mail_metrics_docs: {ctx.metrics_repo._col.count_documents({})}")
        print(f"  reviews_pending: {ctx.review_repo.count_pending()}")

        if errors:
            print(f"\n{errors} Endpoint(s) fehlgeschlagen")
            return 1
        print("\nAlle API-Checks OK")
        return 0
    except Exception as exc:
        print(f"FEHLER: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
