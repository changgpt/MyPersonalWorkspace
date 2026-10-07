"""Human-readable dates for display.

Everything is stored as ISO text ("2026-10-07"), which is right for the
database but reads like a database when rendered -- so templates run dates
through the `human_date` Jinja filter instead (registered in __init__.py
next to `markdown`). Display only: an `<input type="date">` value must stay
ISO, so those are never filtered.

Pure functions, no DB or network, like markdown_utils/greetings/internship.
"""
from datetime import date, datetime

# Day-of-month is interpolated rather than using strftime("%-d"), which is
# a glibc/macOS extension that raises on Windows (same reason as the
# internship end date in dashboard.py).
_SHORT = "{d.day} {month}"
_WITH_YEAR = "{d.day} {month} {d.year}"
_WITH_WEEKDAY = "{weekday} {d.day} {month}"


def parse_iso(value):
    """A date from an ISO date string, an ISO timestamp, a datetime or a
    date. None for anything unparseable, so callers can fall back."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None


def human_date(value, today=None):
    """"Today" / "Yesterday" / "Tomorrow" for the days either side of now,
    a weekday for the rest of the surrounding week ("Mon 5 Oct" -- the date
    stays on so a bare weekday can't be read as the wrong week), then
    "5 Oct", and "5 Oct 2025" once the year differs. Returns the input
    unchanged if it isn't a date at all."""
    parsed = parse_iso(value)
    if parsed is None:
        return value if value is not None else ""
    today = today or date.today()
    days_away = (parsed - today).days
    if days_away == 0:
        return "Today"
    if days_away == -1:
        return "Yesterday"
    if days_away == 1:
        return "Tomorrow"
    month = f"{parsed:%b}"
    if -6 <= days_away <= 6:
        return _WITH_WEEKDAY.format(weekday=f"{parsed:%a}", d=parsed, month=month)
    if parsed.year == today.year:
        return _SHORT.format(d=parsed, month=month)
    return _WITH_YEAR.format(d=parsed, month=month)


def human_date_range(start, end, today=None):
    """One line for a week: "5 - 11 Oct" (or "28 Sep - 4 Oct" across a
    month boundary), prefixed with "This week" when today falls inside."""
    first, last = parse_iso(start), parse_iso(end)
    if first is None or last is None:
        return ""
    today = today or date.today()
    if first.month == last.month:
        span = f"{first.day} - {last.day} {last:%b}"
    else:
        span = f"{first.day} {first:%b} - {last.day} {last:%b}"
    if first.year != today.year or last.year != today.year:
        span += f" {last.year}"
    return f"This week · {span}" if first <= today <= last else span
