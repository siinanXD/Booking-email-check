#!/usr/bin/env python3
"""Cursor afterFileEdit-Hook: formatiert vom Agenten geänderte Dateien.

Vertrag (Cursor Hooks, Beta): Cursor schickt ein JSON-Payload auf stdin und
liest optional JSON auf stdout. Exit-Code 0 = ok. Wir nutzen den Hook nur, um
jede gerade geänderte Python-Datei sofort lint-/format-konform zu machen,
damit es gar nicht erst zu einem unsauberen Commit kommt.

Hinweis: Das Hook-Schema ist in Cursor noch Beta. Prüfe die Feldnamen des
Payloads (insb. 'file_path') gegen die aktuelle Cursor-Doku, falls sich das
Format geändert hat.
"""

from __future__ import annotations

import json
import subprocess
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    file_path = payload.get("file_path", "")
    if not file_path.endswith(".py"):
        return 0

    subprocess.run(["ruff", "check", "--fix", file_path], check=False)
    subprocess.run(["ruff", "format", file_path], check=False)
    subprocess.run(["black", file_path], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
