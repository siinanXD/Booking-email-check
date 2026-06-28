"""Extraktions-Genauigkeit als Report ("Dashboard").

Misst die deterministisch angereicherten Felder (Zimmer, Kanal …) über das
Golden-Set — pro Feld und pro Kanal, ohne LLM/Kosten.

    python scripts/eval_extraction.py
    python scripts/eval_extraction.py --json eval_report.json --min 1.0

Für die LLM-Extraktionsqualität (Intent/Datum/Buchungsnummer) zusätzlich:
    EVAL_LLM_MODE=live pytest tests/eval/test_offline_eval.py -s
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.ai.eval.field_accuracy import evaluate_deterministic  # noqa: E402

_DEFAULT_GOLDEN = _REPO_ROOT / "tests" / "eval" / "extraction_golden.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Extraktions-Feldgenauigkeit")
    parser.add_argument("--golden", type=Path, default=_DEFAULT_GOLDEN)
    parser.add_argument(
        "--json", type=Path, default=None, help="Report als JSON ablegen"
    )
    parser.add_argument(
        "--min",
        type=float,
        default=0.0,
        help="Mindest-Gesamtgenauigkeit; darunter Exit-Code 1 (für CI)",
    )
    args = parser.parse_args()

    cases = json.loads(args.golden.read_text(encoding="utf-8"))
    report = evaluate_deterministic(cases)
    print(report.render_table())

    if args.json is not None:
        args.json.write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nReport geschrieben: {args.json}")

    if report.overall.accuracy < args.min:
        print(
            f"\nFEHLER: Genauigkeit {report.overall.accuracy:.0%} "
            f"< Mindestwert {args.min:.0%}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
