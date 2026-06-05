"""Erstellt den Atlas Vector Search Index für Embeddings.

Benötigt einen MongoDB Atlas M10+-Cluster (kein Community-MongoDB).

Verwendung:
    python scripts/setup_atlas_vector_index.py          # erstellt Index
    python scripts/setup_atlas_vector_index.py --check  # prüft nur ob Index existiert

Der Index-Name muss mit VECTOR_INDEX_NAME in embedding_repository.py übereinstimmen:
    "embedding_vector_index"

Dimensionen und Similarity:
    - text-embedding-3-small: 1536 Dimensionen (Standard)
    - text-embedding-3-large: 3072 Dimensionen (EMBEDDING_MODEL=text-embedding-3-large)
    Änderung: Konstante DIMENSIONS unten anpassen.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from backend.core.config.settings import get_settings
    from backend.infrastructure.repositories.mongo import get_client
except ModuleNotFoundError as exc:
    print(f"Import fehlgeschlagen – venv aktiviert? Details: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc

INDEX_NAME = "embedding_vector_index"
COLLECTION_NAME = "embeddings"
DIMENSIONS = 1536  # text-embedding-3-small; für -large: 3072
SIMILARITY = "cosine"


def _index_exists(collection: object) -> bool:
    try:
        indexes = list(collection.list_search_indexes())  # type: ignore[attr-defined]
        return any(idx.get("name") == INDEX_NAME for idx in indexes)
    except Exception:
        return False


def check_index(collection: object) -> bool:
    """Gibt True zurück wenn der Index existiert."""
    if _index_exists(collection):
        print(f"✓ Index '{INDEX_NAME}' existiert bereits.")
        return True
    print(f"✗ Index '{INDEX_NAME}' nicht gefunden.")
    _print_manual_instructions()
    return False


def create_index(collection: object) -> None:
    """Erstellt den Vector Search Index falls nicht vorhanden."""
    if _index_exists(collection):
        print(f"✓ Index '{INDEX_NAME}' existiert bereits – nichts zu tun.")
        return

    try:
        from pymongo.operations import SearchIndexModel

        model = SearchIndexModel(
            definition={
                "fields": [
                    {
                        "type": "vector",
                        "path": "embedding",
                        "numDimensions": DIMENSIONS,
                        "similarity": SIMILARITY,
                    }
                ]
            },
            name=INDEX_NAME,
            type="vectorSearch",
        )
        collection.create_search_index(model)  # type: ignore[attr-defined]
        print(
            f"✓ Index '{INDEX_NAME}' wird erstellt (dauert ~1-2 Minuten im Atlas).\n"
            f"  Prüfen: python scripts/setup_atlas_vector_index.py --check"
        )
    except Exception as exc:
        err = str(exc)
        if "not supported" in err.lower() or "not available" in err.lower():
            print(
                f"✗ Atlas Vector Search nicht verfügbar (kein Atlas M10+-Cluster?).\n"
                f"  Fehler: {err}"
            )
        else:
            print(f"✗ Index-Erstellung fehlgeschlagen: {err}")
        _print_manual_instructions()
        raise SystemExit(1) from exc


def _print_manual_instructions() -> None:
    print(
        "\n── Manueller Setup (Atlas UI) ──────────────────────────────────────\n"
        "1. Atlas → Datenbank → Search → Create Search Index\n"
        "2. Typ: Vector Search\n"
        f"3. Index Name: {INDEX_NAME}\n"
        f"4. Collection: <db_name>.{COLLECTION_NAME}\n"
        "5. JSON-Definition:\n"
        "   {\n"
        '     "fields": [{\n'
        '       "type": "vector",\n'
        '       "path": "embedding",\n'
        f'       "numDimensions": {DIMENSIONS},\n'
        f'       "similarity": "{SIMILARITY}"\n'
        "     }]\n"
        "   }\n"
        "────────────────────────────────────────────────────────────────────"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Nur prüfen ob der Index existiert, nicht erstellen",
    )
    args = parser.parse_args()

    settings = get_settings()
    client = get_client(settings)
    db = client[settings.mongodb_db_name]
    collection = db[COLLECTION_NAME]

    if args.check:
        sys.exit(0 if check_index(collection) else 1)
    else:
        create_index(collection)


if __name__ == "__main__":
    main()
