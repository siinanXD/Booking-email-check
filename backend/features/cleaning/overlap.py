"""Erkennung doppelt belegter Zimmer (überlappende Aufenthalte)."""

from __future__ import annotations

from datetime import date

from backend.features.cleaning.models import CleaningTask, CleaningTaskStatus


def overlapping_task_ids(tasks: list[CleaningTask]) -> set[str]:
    """Task-IDs, deren Zimmer mit überlappenden Aufenthaltsdaten doppelt belegt ist.

    Gruppiert nach (Wohnung, Zimmer); innerhalb einer Gruppe überlappen zwei
    Aufenthalte, wenn ``a.check_in < b.check_out`` und ``b.check_in < a.check_out``
    (nahtloser Wechsel check_out == check_in gilt NICHT als Konflikt). Stornierte
    Aufträge und solche ohne Datumsangaben zählen nicht.
    """
    groups: dict[tuple[str, str], list[CleaningTask]] = {}
    for task in tasks:
        if task.status == CleaningTaskStatus.CANCELLED:
            continue
        if task.check_in is None or task.check_out is None:
            continue
        key = (
            (task.property_name or "").strip().lower(),
            (task.room_number or "").strip(),
        )
        groups.setdefault(key, []).append(task)

    flagged: set[str] = set()
    for members in groups.values():
        ordered = sorted(members, key=lambda t: t.check_in or date.min)
        for i, first in enumerate(ordered):
            for second in ordered[i + 1 :]:
                assert first.check_in and first.check_out
                assert second.check_in and second.check_out
                if second.check_in >= first.check_out:
                    break  # nach Startdatum sortiert → keine weiteren Überlappungen
                flagged.add(first.task_id)
                flagged.add(second.task_id)
    return flagged
