"""Lädt Prompt-Templates aus dem prompts/-Verzeichnis."""

from __future__ import annotations

import json
from pathlib import Path

_PROMPTS_ROOT = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(relative_path: str) -> str:
    """Lädt eine Markdown-Prompt-Datei."""
    path = _PROMPTS_ROOT / relative_path
    return path.read_text(encoding="utf-8")


def load_few_shot_examples(relative_path: str) -> list[dict[str, object]]:
    """Lädt Few-Shot-Beispiele aus JSON."""
    path = _PROMPTS_ROOT / relative_path
    data: list[dict[str, object]] = json.loads(path.read_text(encoding="utf-8"))
    return data


def format_few_shots(examples: list[dict[str, object]], style: str = "classify") -> str:
    """Formatiert Few-Shots als Textblock für Prompts."""
    lines: list[str] = []
    for ex in examples:
        if style == "classify":
            lines.append(
                f"Beispiel: Betreff={ex.get('subject')} -> intent={ex.get('intent')}"
            )
        else:
            payload = ex.get("output", ex)
            lines.append(f"Beispiel: {json.dumps(payload, ensure_ascii=False)}")
    return "\n".join(lines)


def format_prompt(relative_path: str, **kwargs: str) -> str:
    """Lädt und formatiert ein Template."""
    template = load_prompt(relative_path)
    return template.format(**kwargs)


def format_prompt_with_few_shots(
    relative_path: str,
    few_shot_path: str,
    few_shot_style: str = "classify",
    **kwargs: str,
) -> str:
    """Prompt inkl. Few-Shot-Block."""
    few_shots = format_few_shots(
        load_few_shot_examples(few_shot_path),
        style=few_shot_style,
    )
    base = format_prompt(relative_path, **kwargs)
    return f"{few_shots}\n\n{base}"
