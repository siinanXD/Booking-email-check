"""Gemeinsamer Start für CLI-Skripte: Projektroot + venv-Hinweis."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def setup_path() -> Path:
    """Projektroot auf sys.path; gibt ROOT zurück."""
    root_str = str(ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return ROOT


def require_project_venv() -> None:
    """Beendet mit Hinweis, wenn zentrale Abhängigkeiten fehlen (falsches Python)."""
    setup_path()
    try:
        import langfuse  # noqa: F401
    except ImportError:
        venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
        script = Path(sys.argv[0]).name
        print(
            "FEHLER: Modul 'langfuse' nicht gefunden.\n"
            "Die Skripte müssen mit dem Projekt-venv laufen,\n"
            "nicht mit globalem python.\n\n"
            f"  .\\.venv\\Scripts\\Activate.ps1\n"
            f"  python scripts\\{script}\n\n"
            f"oder direkt:\n  {venv_py} scripts\\{script}",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


def safe_print(text: str) -> None:
    """Konsolen-Ausgabe ohne UnicodeEncodeError unter Windows."""
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode(enc, errors="replace").decode(enc))
