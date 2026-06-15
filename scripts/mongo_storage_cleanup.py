"""Atlas-Speicher analysieren und gezielt aufräumen (M0 512-MB-Quota).

Wenn der Cluster über seiner Quota liegt, blockiert Atlas alle Schreib- und
Index-Operationen — die App crasht dann schon beim Boot (create_index in jedem
Repository-__init__). Dieses Skript zeigt, welche Collections den Platz fressen,
und räumt auf Wunsch die größten, gefahrlos löschbaren Daten weg.

Standardmäßig DRY-RUN (es wird nichts verändert). Erst mit ``--apply`` wird
gelöscht.

Beispiele:
    # Nur analysieren — welche Collection ist wie groß?
    python scripts/mongo_storage_cleanup.py

    # LangGraph-Checkpoints droppen (verliert nur laufende Review-Resumes)
    python scripts/mongo_storage_cleanup.py --drop-checkpoints --apply

    # Mails älter als 90 Tage löschen + Checkpoints droppen
    python scripts/mongo_storage_cleanup.py --drop-checkpoints --prune-emails 90 --apply

Hinweis zur Quota: Atlas erlaubt über der Quota normalerweise weiterhin
``delete``/``drop`` (zum Freiräumen), aber keine Inserts/Updates/Index-Builds.
``drop()`` (Checkpoints) ist am zuverlässigsten; ``deleteMany`` (Mail-Pruning)
kann je nach Sperre fehlschlagen — dann zuerst die Checkpoints droppen.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.config.settings import get_settings
from backend.infrastructure.repositories.mongo import get_client

# LangGraph MongoDBSaver Default-Collections (siehe checkpointer.py).
CHECKPOINT_COLLECTIONS = ("checkpoints", "checkpoint_writes")


def _human(num_bytes: float) -> str:
    """Bytes als MB/GB-String."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:6.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:6.1f} TB"


def _collstats(db: Any, name: str) -> dict[str, Any]:
    """collStats für eine Collection (leer bei Fehler)."""
    try:
        return dict(db.command("collStats", name))
    except Exception as exc:  # noqa: BLE001 - Diagnose soll nie hart crashen
        return {"_error": str(exc)}


def _report(db: Any, top: int) -> None:
    """Tabelle der größten Collections (Daten + Indexe) ausgeben."""
    names = db.list_collection_names()
    rows: list[tuple[str, int, int, int]] = []
    for name in names:
        stats = _collstats(db, name)
        if "_error" in stats:
            print(f"  ! {name}: {stats['_error']}")
            continue
        storage = int(stats.get("storageSize", 0))
        index = int(stats.get("totalIndexSize", 0))
        count = int(stats.get("count", 0))
        rows.append((name, storage, index, count))

    rows.sort(key=lambda r: r[1] + r[2], reverse=True)

    try:
        db_stats = dict(db.command("dbStats"))
        total = int(db_stats.get("storageSize", 0)) + int(db_stats.get("indexSize", 0))
        print(f"\n=== {db.name}: ~{_human(total)} belegt (storage + index) ===\n")
    except Exception as exc:  # noqa: BLE001
        print(f"\n=== {db.name} (dbStats fehlgeschlagen: {exc}) ===\n")

    print(f"{'Collection':<32} {'Storage':>12} {'Index':>12} {'Docs':>10}")
    print("-" * 70)
    for name, storage, index, count in rows[:top]:
        print(f"{name:<32} {_human(storage):>12} {_human(index):>12} {count:>10,}")
    if len(rows) > top:
        print(f"... und {len(rows) - top} weitere Collections")


def _drop_checkpoints(db: Any, *, apply: bool) -> None:
    """LangGraph-Checkpoint-Collections droppen."""
    existing = set(db.list_collection_names())
    for name in CHECKPOINT_COLLECTIONS:
        if name not in existing:
            print(f"  - {name}: nicht vorhanden, übersprungen")
            continue
        stats = _collstats(db, name)
        size = int(stats.get("storageSize", 0)) + int(stats.get("totalIndexSize", 0))
        if not apply:
            print(f"  [dry-run] würde droppen: {name} (~{_human(size)})")
            continue
        try:
            db.drop_collection(name)
            print(f"  ✓ gedroppt: {name} (~{_human(size)} frei)")
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ {name}: drop fehlgeschlagen — {exc}")


def _prune_emails(db: Any, days: int, *, apply: bool) -> None:
    """Mails älter als N Tage löschen (received_at, ISO-String-Vergleich)."""
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    query = {"received_at": {"$lt": cutoff}}
    col = db["emails"]
    try:
        count = int(col.count_documents(query))
    except Exception as exc:  # noqa: BLE001
        print(f"  ✗ emails: count fehlgeschlagen — {exc}")
        return

    if not apply:
        print(f"  [dry-run] würde {count:,} Mails vor {cutoff} löschen")
        return
    if count == 0:
        print(f"  - keine Mails vor {cutoff}")
        return
    try:
        result = col.delete_many(query)
        print(f"  ✓ {result.deleted_count:,} Mails vor {cutoff} gelöscht")
    except Exception as exc:  # noqa: BLE001
        print(f"  ✗ emails: delete fehlgeschlagen (Quota-Sperre?) — {exc}")


def main() -> None:
    """CLI-Einstieg."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Änderungen wirklich ausführen (sonst Dry-Run).",
    )
    parser.add_argument(
        "--drop-checkpoints",
        action="store_true",
        help="LangGraph-Checkpoint-Collections droppen.",
    )
    parser.add_argument(
        "--prune-emails",
        type=int,
        metavar="DAYS",
        help="Mails löschen, die älter als DAYS Tage sind.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Wie viele Collections im Report anzeigen (Default 20).",
    )
    args = parser.parse_args()

    settings = get_settings()
    client = get_client(settings)
    db = client[settings.mongodb_db_name]

    print(f"Verbunden mit DB '{db.name}'")
    if not args.apply:
        print(">>> DRY-RUN — es wird nichts verändert (--apply zum Ausführen)\n")

    _report(db, args.top)

    if args.drop_checkpoints:
        print("\n--- LangGraph-Checkpoints ---")
        _drop_checkpoints(db, apply=args.apply)

    if args.prune_emails is not None:
        print(f"\n--- Mail-Pruning (> {args.prune_emails} Tage) ---")
        _prune_emails(db, args.prune_emails, apply=args.apply)

    if args.apply and (args.drop_checkpoints or args.prune_emails is not None):
        print("\nNeuer Stand:")
        _report(db, args.top)


if __name__ == "__main__":
    main()
