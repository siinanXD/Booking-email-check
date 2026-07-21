"""Deterministische Auflösung relativer Zeitangaben (kein LLM-Raten).

Relative Ausdrücke wie "morgen" oder "nächste Woche" werden in Python in
konkrete Datumsbereiche übersetzt — in der Zeitzone des Mandanten.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = "Europe/Berlin"

# Der Schlusspunkt ist optional: "24.07" schrieb der Kunde ohne, und ohne
# diese Freiheit fiel der Startwert eines Bereichs komplett weg.
_DATE_PATTERN = re.compile(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?")
_TIME_SUFFIX = re.compile(r"\s*uhr\b")


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


def _safe_date(year: int, month: int, day: int) -> date | None:
    """date() ohne Exception — ungültige Kombinationen ergeben None."""
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _full_year(raw: str) -> int:
    year = int(raw)
    return year + 2000 if year < 100 else year


def _parse_explicit_dates(text: str, today: date) -> tuple[date, date] | None:
    """Erkennt "12.08" / "12.08." / "12.08.2026" (einzeln oder als Bereich)."""
    raw: list[tuple[int, int, str | None]] = []
    for match in _DATE_PATTERN.finditer(text):
        if _TIME_SUFFIX.match(text, match.end()):
            continue  # "12.08 Uhr" ist eine Uhrzeit, kein Datum
        raw.append((int(match.group(1)), int(match.group(2)), match.group(3)))
    if not raw:
        return None

    # Nennt ein Datum des Bereichs ein Jahr, gilt es auch für das andere:
    # "24.07 - 27.07.2026" meint beide Male 2026, nicht das aktuelle Jahr.
    stated = next((_full_year(year) for _, _, year in raw if year), None)
    found: list[date] = []
    for day, month, year_raw in raw[:2]:
        if year_raw:
            candidate = _safe_date(_full_year(year_raw), month, day)
        elif stated is not None:
            candidate = _safe_date(stated, month, day)
        else:
            candidate = _safe_date(today.year, month, day)
            # Ohne jede Jahresangabe: Vergangenes rutscht ins nächste Jahr.
            if candidate is not None and candidate < today:
                candidate = _safe_date(today.year + 1, month, day)
        if candidate is not None:
            found.append(candidate)

    if not found:
        return None
    if len(found) == 1:
        return found[0], found[0]
    start, end = found[0], found[1]
    if start > end:
        # Jahreswechsel im Bereich: "28.12 - 03.01.2027" beginnt 2026.
        wrapped = _safe_date(start.year - 1, start.month, start.day)
        if not raw[0][2] and start.month > end.month and wrapped is not None:
            return wrapped, end
        return end, start
    return start, end


def format_date(value: date | None) -> str:
    """Deutsches Kurzformat (TT.MM.JJJJ)."""
    return value.strftime("%d.%m.%Y") if value else "—"
