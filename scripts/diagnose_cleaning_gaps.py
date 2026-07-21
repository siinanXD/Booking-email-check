"""Findet Buchungen, zu denen kein Putzauftrag existiert (nur lesend).

Hintergrund: Putzaufträge entstehen an genau zwei Stellen — im Live-Pfad
(`cleaning_hook` / `pipeline_review`) beim Eintreffen der Mail, und einmalig
im Backfill, den ausschließlich das Umlegen des Feature-Schalters auslöst
(`admin.py`, `POST /admin/accounts/<id>/features`). Es gibt keinen Job, der
später erneut aufräumt. Fällt eine Buchung einmal durch — Extraktionsfehler,
fehlendes Check-out, abweichender Intent, Ausfall —, fehlt sie dauerhaft und
ohne Fehlermeldung.

Dieses Skript vergleicht `extractions` gegen `cleaning_tasks` und nennt je
Lücke den Grund. Es schreibt nichts.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import UTC, datetime
from typing import Any, NamedTuple

from _bootstrap import require_project_venv, safe_print

require_project_venv()

from backend.core.config.settings import Settings  # noqa: E402
from backend.features.cleaning.models import (  # noqa: E402
    SOURCE_CANCELLATION_EMAIL,
    CleaningTask,
    CleaningTaskStatus,
)
from backend.infrastructure.repositories.mongo import get_database  # noqa: E402

_SCHEDULING_INTENTS = ("new_booking", "change")


def _accounts(db: Any) -> list[str]:
    return sorted(
        {
            str(d["account_id"])
            for d in db["extractions"].find({}, {"account_id": 1})
            if d.get("account_id")
        }
    )


class Finding(NamedTuple):
    """Eine Auffälligkeit; `task_id` nur, wenn sie reparierbar ist."""

    reason: str
    task_id: str | None = None


def _reason(
    db: Any, account_id: str, doc: dict[str, Any], has_task: bool
) -> Finding | None:
    """Warum fehlt der Auftrag? None = alles in Ordnung."""
    extraction = doc.get("extraction") or {}
    if not extraction.get("check_out"):
        # cleaning_date_for() liefert None; der Auftrag taucht in keiner
        # Zeitraum-Abfrage auf, auch wenn er angelegt wurde.
        return Finding("check_out fehlt in der Extraktion")
    intent = extraction.get("intent")
    if intent == "cancellation":
        # Ein Storno legt bewusst keinen eigenen Auftrag an, es storniert den
        # bestehenden. Auffaellig ist nur der Auftrag, der danach WIEDER aktiv
        # ist — vor dem Reopen-Guard weckte jede erneut verarbeitete Altmail
        # stornierte Auftraege wieder auf.
        booking_number = extraction.get("booking_number")
        if not booking_number:
            return None
        task = db["cleaning_tasks"].find_one(
            {"account_id": account_id, "booking_number": booking_number}
        )
        if task is None:
            return Finding("Storno ohne zugehoerigen Auftrag")
        if task.get("status") != "cancelled":
            return Finding(
                f"STORNO NICHT WIRKSAM — Auftrag steht auf {task.get('status')!r}",
                str(task["_id"]),
            )
        return None
    if intent not in _SCHEDULING_INTENTS:
        return Finding(f"Intent {intent!r} legt keinen Auftrag an")
    if not has_task:
        return Finding("kein Putzauftrag zur correlation_id")
    return None


def _repair(db: Any, task_ids: list[str]) -> None:
    """Setzt wiederbelebte Auftraege zurueck auf storniert (kein Versand)."""
    for task_id in task_ids:
        doc = db["cleaning_tasks"].find_one({"_id": task_id})
        if doc is None:
            continue
        task = CleaningTask.from_mongo(doc)
        task.record_status(
            CleaningTaskStatus.CANCELLED,
            source=SOURCE_CANCELLATION_EMAIL,
            note="storno_nachgezogen",
        )
        payload = task.to_mongo()
        payload["account_id"] = task.account_id
        db["cleaning_tasks"].update_one({"_id": task_id}, {"$set": payload})
        safe_print(f"  STORNIERT  {task_id[:10]} {task.guest_name!r}")


def _report(
    db: Any, account_id: str, today: str, verbose: bool
) -> tuple[Counter[str], list[str]]:
    """Lücken eines Mandanten ausgeben, Gründe zählen, Reparierbare sammeln."""
    task_cids = {
        str(d["correlation_id"])
        for d in db["cleaning_tasks"].find(
            {"account_id": account_id}, {"correlation_id": 1}
        )
        if d.get("correlation_id")
    }
    undated = db["cleaning_tasks"].count_documents(
        {"account_id": account_id, "cleaning_date": None}
    )
    if undated:
        safe_print(
            f"  WARNUNG  {undated} Auftraege ohne cleaning_date — "
            "unsichtbar in jedem Putzplan-Zeitraum"
        )

    reasons: Counter[str] = Counter()
    repairable: list[str] = []
    # Kein Datumsfilter im Query: eine Buchung mit fehlendem check_out laesst
    # sich nicht nach Datum filtern, waere aber genau der interessante Fall.
    for doc in db["extractions"].find({"account_id": account_id}):
        extraction = doc.get("extraction") or {}
        check_out = extraction.get("check_out") or ""
        check_in = extraction.get("check_in") or ""
        if max(check_out, check_in) < today:
            continue  # rein historisch, fuer den Putzplan irrelevant
        finding = _reason(db, account_id, doc, str(doc["_id"]) in task_cids)
        if finding is None:
            continue
        reasons[finding.reason] += 1
        if finding.task_id and finding.task_id not in repairable:
            repairable.append(finding.task_id)
        if verbose:
            safe_print(
                f"  LUECKE   {str(doc['_id'])[:12]} "
                f"{extraction.get('property_name')!r} "
                f"Zi={extraction.get('room_number')} "
                f"Gast={extraction.get('guest_name')!r} "
                f"in={check_in or '-'} out={check_out or '-'} "
                f"-> {finding.reason}"
            )
    return reasons, repairable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", help="nur dieser Mandant")
    parser.add_argument(
        "--quiet", action="store_true", help="nur Zusammenfassung, keine Einzelfaelle"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="wiederbelebte Auftraege zurueck auf storniert setzen",
    )
    args = parser.parse_args()

    db = get_database(Settings())
    today = datetime.now(UTC).date().isoformat()
    accounts = [args.account] if args.account else _accounts(db)

    total: Counter[str] = Counter()
    repairable: list[str] = []
    for account_id in accounts:
        safe_print(f"\n=== {account_id} ===")
        reasons, fixable = _report(db, account_id, today, verbose=not args.quiet)
        if not reasons:
            safe_print("  Keine Luecken.")
        total.update(reasons)
        repairable.extend(fixable)

    safe_print("\n--- Zusammenfassung ---")
    for reason, count in total.most_common():
        safe_print(f"  {count:4d}  {reason}")
    safe_print(f"  {sum(total.values()):4d}  Luecken gesamt (Stichtag {today})")

    if not repairable:
        return 0
    if not args.apply:
        safe_print(
            f"\n{len(repairable)} Auftraege waeren reparierbar. "
            "TROCKENLAUF — nichts geschrieben. Mit --apply ausfuehren."
        )
        return 0
    safe_print("")
    _repair(db, repairable)
    safe_print(
        f"\n{len(repairable)} Auftraege storniert. ACHTUNG: bereits versendete "
        "WhatsApp-Auftraege werden dadurch NICHT zurueckgezogen — betroffene "
        "Putzkraefte muessen von Hand informiert werden."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
