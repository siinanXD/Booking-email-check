#!/usr/bin/env python3
"""Cursor beforeShellExecution-Hook: blockiert riskante Git-Befehle.

Dieser Hook ist die technische Durchsetzung der Regel „kein Direkt-Push auf
main“. Cursor reicht den geplanten Shell-Befehl als JSON auf stdin; wir
antworten mit JSON auf stdout. Ein Feld 'permission' steuert, ob Cursor den
Befehl ausführt.

Hinweis: Cursor Hooks sind Beta. Das Antwortschema kann sich ändern – gegen die
aktuelle Cursor-Doku prüfen. Bei Parse-Fehlern fail-open; harte Schranke bleibt
Branch-Protection auf 'main'.
"""

from __future__ import annotations

import json
import re
import sys

BLOCKED_PATTERNS = [
    r"\bgit\s+push\b.*\bmain\b",
    r"\bgit\s+push\b.*\borigin\s+main",
    r"\bgit\s+push\s+--force\b",
    r"\bgit\s+push\s+-f\b",
]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"permission": "allow"}))
        return 0

    command = str(payload.get("command", ""))

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command):
            print(
                json.dumps(
                    {
                        "permission": "deny",
                        "userMessage": (
                            "Direkter Push/Force-Push auf 'main' ist gesperrt. "
                            "Nutze einen Feature-Branch und einen PR mit grüner CI."
                        ),
                    }
                )
            )
            return 0

    print(json.dumps({"permission": "allow"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
