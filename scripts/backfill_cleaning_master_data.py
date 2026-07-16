"""Zieht Zimmer/Objekt/Gast bestehender Putzaufträge aus den Mails nach.

Hintergrund: Der Zimmer-Fix vom 3. Juli (210ad55) reparierte den Parser, aber
`_update_existing` schrieb die Stammdaten nie mit — vorher angelegte Aufträge
behielten ihr `room_number=None`, obwohl "Zimmer Nr. 3" wörtlich in der Mail
stand. Im Putzplan sah es dadurch so aus, als erkenne die Software die Zimmer
nicht; tatsächlich waren nur die Altdaten eingefroren.

Angereichert wird aus `emails` + der rohen LLM-Ausgabe in `extractions`, exakt
wie im Live-Pfad (`enrich_extraction`). Die `extractions`-Collection allein
genügt nicht: sie speichert die Ausgabe VOR der Anreicherung und führt
`room_number`/`channel` gar nicht.

Zusätzlich werden Phantom-Objekte erkannt: Unterkünfte, deren Name eine andere
Unterkunft als ganze Wortfolge enthält ("Münzbach Ferienzimmer Zimmer Nr. 3"
enthält "Münzbach Ferienzimmer"). Das Zimmer ist dort in den Objektnamen
gerutscht. Sie werden archiviert, ihre Aufträge auf das echte Objekt gezogen.

Standard ist der Trockenlauf. Erst `--apply` schreibt.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from backend.ai.domain.booking.extraction import BookingExtraction
from backend.ai.domain.booking.extraction_enrichment import enrich_extraction
from backend.ai.domain.booking.property_match import match_known_property_name
from backend.core.config.settings import Settings
from backend.core.models.email import StoredEmail
from backend.features.cleaning.models import SOURCE_BACKFILL, CleaningTask
from backend.infrastructure.repositories.mongo import get_database

_FIELDS = ("room_number", "property_name", "guest_name")


def _real_properties(db: Any, account_id: str) -> tuple[list[str], dict[str, str]]:
    """Echte Objekte + Zuordnung Phantom-Name -> echter Name."""
    # Altbestände haben kein `active`-Feld — `$ne: False` zählt sie als aktiv
    # (konsistent zu PropertyRepository). Archivierte Phantome bleiben draußen,
    # damit ein zweiter Lauf sie nicht erneut meldet.
    names = [
        str(d.get("name") or "").strip()
        for d in db["properties"].find(
            {"account_id": account_id, "active": {"$ne": False}}, {"name": 1}
        )
        if str(d.get("name") or "").strip()
    ]
    phantoms: dict[str, str] = {}
    for name in names:
        others = [n for n in names if n != name]
        hit = match_known_property_name(name, others)
        if hit:
            phantoms[name] = hit
    real = [n for n in names if n not in phantoms]
    return real, phantoms


def _email_for(db: Any, correlation_id: str) -> StoredEmail | None:
    # `_id` der Mail ist die message_id, nicht die correlation_id.
    doc = db["emails"].find_one({"correlation_id": correlation_id})
    if doc is None:
        return None
    payload = {k: v for k, v in doc.items() if k != "_id"}
    payload.setdefault("correlation_id", correlation_id)
    try:
        return StoredEmail.model_validate(payload)
    except Exception:
        return None


def _enriched_for(
    db: Any, email: StoredEmail, catalog: list[str]
) -> BookingExtraction | None:
    doc = db["extractions"].find_one({"message_id": email.message_id})
    raw = (doc or {}).get("extraction") or {}
    try:
        base = BookingExtraction.model_validate(raw)
    except Exception:
        return None
    return enrich_extraction(email, base, known_property_names=catalog)


def _plan(
    db: Any,
) -> tuple[list[str], list[tuple[CleaningTask, dict[str, Any]]], list[str]]:
    lines: list[str] = []
    updates: list[tuple[CleaningTask, dict[str, Any]]] = []
    archive: list[str] = []

    accounts = {
        str(d["account_id"])
        for d in db["cleaning_tasks"].find({}, {"account_id": 1})
        if d.get("account_id")
    }
    for account_id in sorted(accounts):
        catalog, phantoms = _real_properties(db, account_id)
        for phantom, real in phantoms.items():
            lines.append(f"  PHANTOM  {phantom!r} -> archivieren (echt: {real!r})")
            archive.extend(
                str(d["_id"])
                for d in db["properties"].find(
                    {"account_id": account_id, "name": phantom}, {"_id": 1}
                )
            )

        for doc in db["cleaning_tasks"].find({"account_id": account_id}):
            task = CleaningTask.from_mongo(doc)
            if not task.correlation_id:
                continue
            email = _email_for(db, task.correlation_id)
            if email is None:
                continue
            fresh = _enriched_for(db, email, catalog)
            if fresh is None:
                continue
            changes = {
                f: getattr(fresh, f)
                for f in _FIELDS
                if getattr(fresh, f) and getattr(fresh, f) != getattr(task, f)
            }
            if not changes:
                continue
            before = {f: getattr(task, f) for f in changes}
            lines.append(
                f"  KORREKTUR  {task.task_id[:10]} "
                f"{task.property_name!r}: {before} -> {changes}"
            )
            updates.append((task, changes))
    return lines, updates, archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Änderungen schreiben")
    args = parser.parse_args()

    db = get_database(Settings())
    lines, updates, archive = _plan(db)
    print("\n".join(lines) if lines else "Nichts zu tun.")
    print(f"\n{len(updates)} Auftraege, {len(archive)} Phantom-Objekte.")

    if not args.apply:
        print("TROCKENLAUF — nichts geschrieben. Mit --apply ausführen.")
        return 0

    for task, changes in updates:
        for field, value in changes.items():
            setattr(task, field, value)
        task.record_status(task.status, source=SOURCE_BACKFILL, note="master_data")
        doc = task.to_mongo()
        doc["account_id"] = task.account_id
        db["cleaning_tasks"].update_one({"_id": task.task_id}, {"$set": doc})
    for property_id in archive:
        db["properties"].update_one({"_id": property_id}, {"$set": {"active": False}})
    print(f"Geschrieben: {len(updates)} Auftraege, {len(archive)} Objekte archiviert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
