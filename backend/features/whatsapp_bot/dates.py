"""Deterministische Auflösung relativer Zeitangaben (kein LLM-Raten).

Relative Ausdrücke wie "morgen" oder "nächste Woche" werden in Python in
konkrete Datumsbereiche übersetzt — in der Zeitzone des Mandanten.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "Europe/Berlin"

_DATE_PATTERN = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})?")


def today_in_tz(timezone: str = DEFAULT_TIMEZONE) -> date:
    """Heutiges Datum in der Mandanten-Zeitzone."""
    try:
        tz = ZoneInfo(timezone)
    except Exception:
        tz = ZoneInfo(DEFAULT_TIMEZONE)
    return datetime.now(tz).date()


def _week_bounds(anchor: date) -> tuple[date, date]:
    start = anchor - timedelta(days=anchor.weekday())
    return start, start + timedelta(days=6)


def resolve_period(
    text: str | None,
    *,
    timezone: str = DEFAULT_TIMEZONE,
    today: date | None = None,
) -> tuple[date, date] | None:
    """Übersetzt eine relative Zeitangabe in (start, ende).

    Unterstützt: heute, morgen, übermorgen, diese/nächste/letzte Woche,
    dieses Wochenende, KW-Angaben ("KW 32") und explizite Datumsangaben
    ("12.08." oder "12.08.2026"). Unbekanntes → None (Rückfrage).
    """
    if not text or not text.strip():
        return None
    now = today or today_in_tz(timezone)
    normalized = text.strip().lower()

    if "übermorgen" in normalized:
        day = now + timedelta(days=2)
        return day, day
    if "morgen" in normalized:
        day = now + timedelta(days=1)
        return day, day
    if "heute" in normalized:
        return now, now
    if "wochenende" in normalized:
        saturday = now + timedelta(days=(5 - now.weekday()) % 7)
        return saturday, saturday + timedelta(days=1)
    if "nächste woche" in normalized or "naechste woche" in normalized:
        return _week_bounds(now + timedelta(days=7))
    if "letzte woche" in normalized:
        return _week_bounds(now - timedelta(days=7))
    if "diese woche" in normalized or normalized == "woche":
        return _week_bounds(now)
    if "monat" in normalized:
        if "nächst" in normalized or "naechst" in normalized:
            anchor = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        else:
            anchor = now.replace(day=1)
        next_month = (anchor + timedelta(days=32)).replace(day=1)
        return anchor, next_month - timedelta(days=1)

    kw_match = re.search(r"kw\s*(\d{1,2})", normalized)
    if kw_match:
        week = int(kw_match.group(1))
        if 1 <= week <= 53:
            year = now.year if week >= now.isocalendar()[1] else now.year + 1
            try:
                start = date.fromisocalendar(year, week, 1)
            except ValueError:
                return None
            return start, start + timedelta(days=6)

    explicit = _parse_explicit_dates(normalized, now)
    if explicit:
        return explicit
    return None


def _parse_explicit_dates(text: str, today: date) -> tuple[date, date] | None:
    """Erkennt "12.08." / "12.08.2026" (einzeln oder als Bereich)."""
    found: list[date] = []
    for match in _DATE_PATTERN.finditer(text):
        day, month = int(match.group(1)), int(match.group(2))
        year_raw = match.group(3)
        year = int(year_raw) if year_raw else today.year
        if year < 100:
            year += 2000
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        # Ohne Jahresangabe: Vergangenes rutscht ins nächste Jahr.
        if not year_raw and candidate < today:
            try:
                candidate = date(year + 1, month, day)
            except ValueError:
                continue
        found.append(candidate)
    if not found:
        return None
    if len(found) == 1:
        return found[0], found[0]
    start, end = min(found[:2]), max(found[:2])
    return start, end


def format_date(value: date | None) -> str:
    """Deutsches Kurzformat (TT.MM.JJJJ)."""
    return value.strftime("%d.%m.%Y") if value else "—"
