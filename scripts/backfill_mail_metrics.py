"""Schätzt API-Kosten für Mails mit Extraktion (wenn noch keine mail_metrics existieren)."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _bootstrap import require_project_venv, safe_print

require_project_venv()

# Grobe Schätzung pro Mail mit Klassifikation + Extraktion + Entwurf
_EST_PROMPT_TOKENS = 1200
_EST_COMPLETION_TOKENS = 400
_COST_PER_1K = 0.002


def main() -> int:
    from config.factory import build_app_context
    from config.settings import get_settings

    ctx = build_app_context(get_settings())
    written = 0
    for doc in ctx.extraction_repo._col.find():
        cid = doc.get("_id")
        if not cid:
            continue
        if ctx.metrics_repo._col.find_one({"_id": cid}) is not None:
            continue
        cost = ((_EST_PROMPT_TOKENS + _EST_COMPLETION_TOKENS) / 1000.0) * _COST_PER_1K
        ctx.metrics_repo.record(
            str(cid),
            cost_usd=round(cost, 6),
            prompt_tokens=_EST_PROMPT_TOKENS,
            completion_tokens=_EST_COMPLETION_TOKENS,
        )
        written += 1
    safe_print(f"mail_metrics: {written} Eintraege geschaetzt angelegt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
