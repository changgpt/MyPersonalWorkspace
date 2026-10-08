"""Turning a flat list of calendar events into the "Coming up" day list.

Pure except for `upcoming()`, which calls a source and caches the result.
Everything here is kept free of COM and network calls on purpose (same
split as `greetings.py`/`markdown_utils.py` vs `ai.py`), so the grouping
and the "no more events today" rule are unit-testable without Outlook.
"""
import datetime as dt
import time

from . import calendar_sources, config

# A Graph round trip is ~300-800ms and a COM profile can be slower, which
# is far too slow to pay on every Dashboard load (and on every click of the
# day arrows). Cached per (offset, days) window in process memory rather
# than in the `setting` table: this is a single-user local app, the data is
# read-only and disposable, and a restart just re-fetches. Short TTL so a
# meeting accepted a minute ago still shows up without a manual refresh.
_CACHE = {}


def clear_cache():
    _CACHE.clear()


def _cached(key, ttl, produce):
    hit = _CACHE.get(key)
    now = time.monotonic()
    if hit and now - hit[0] < ttl:
        return hit[1]
    value = produce()
    _CACHE[key] = (now, value)
    return value


def day_window(offset=0, days=None, today=None):
    """The (first_day, last_day_exclusive) the card is showing.

    `offset` is in whole windows, so the arrows page rather than nudge:
    with the default 3-day window, offset=1 is "the next three days after
    the ones you're looking at". offset=0 always starts at today, which is
    what makes "back to today" just offset=0.
    """
    days = days or config.CALENDAR_DAYS
    today = today or dt.date.today()
    start = today + dt.timedelta(days=offset * days)
    return start, start + dt.timedelta(days=days)


def group_by_day(events, start_day, end_day, now=None):
    """One entry per day in the window, each with its events.

    Returns every day in range even when empty -- the card is a calendar
    strip, so a blank day is information ("nothing on Friday"), not a row
    to drop. Events already finished *today* are filtered out, since the
    card says "coming up"; past days in the window (reachable with the back
    arrow) keep everything, because there "coming up" doesn't apply.
    """
    now = now or dt.datetime.now()
    today = now.date()

    by_day = {}
    for event in events:
        day = event.day
        if day == today and not event.is_all_day and not event.ends_after(now):
            continue
        by_day.setdefault(day, []).append(event)

    days = []
    day = start_day
    while day < end_day:
        items = sorted(by_day.get(day, []), key=lambda e: (not e.is_all_day, e.start))
        days.append({
            "date": day,
            "is_today": day == today,
            "is_past": day < today,
            "events": items,
            # Distinguishes "nothing scheduled" from "the rest of today is
            # clear", which read very differently on the day itself.
            "empty_label": "No more events today" if day == today else "Nothing scheduled",
        })
        day += dt.timedelta(days=1)
    return days


def format_time_range(event):
    """"11:30 - 12:00", or "All day". 24-hour, matching the mock-up and
    avoiding the am/pm ambiguity around noon."""
    if event.is_all_day:
        return "All day"
    return f"{event.start:%H:%M} - {event.end:%H:%M}"


# Above this many attendees, the people field is left empty rather than
# prefilled. Tagging the two people in a 1:1 is the whole point; tagging
# the fifteen on a distribution-list notice would spray fifteen new Person
# rows into the database on one careless save, and none of them would mean
# "I worked with this person". Real calendars are full of the latter.
MAX_PREFILL_PEOPLE = 5


def note_prefill(event):
    """Query args for `GET /notes/new` so "Take notes" opens a note that's
    already about this meeting. Attendees go in as people tags, which is
    what makes a 1:1 in Outlook become a 1:1 note with the person already
    linked (`find_or_create_person` runs on save, as for any tag field)."""
    prefill = {"title": event.subject, "date": event.start.date().isoformat()}
    if event.attendees and len(event.attendees) <= MAX_PREFILL_PEOPLE:
        prefill["people"] = ", ".join(event.attendees)
    return prefill


def upcoming(offset=0, days=None, today=None, source=None):
    """`(days, source_label)` for the card, or raises `CalendarError`.

    Returns `(None, None)` when no source is configured at all -- that's
    "the feature isn't set up", which the template shows as a setup hint
    rather than an error.
    """
    days = days or config.CALENDAR_DAYS
    start_day, end_day = day_window(offset, days, today)

    def produce():
        active = source or calendar_sources.resolve_source()
        if active is None:
            return None, None
        # Widen by a day either side: an event that started yesterday and
        # runs into today still belongs on today's row, and a timezone
        # boundary shouldn't clip the last day.
        events = active.fetch(
            dt.datetime.combine(start_day - dt.timedelta(days=1), dt.time.min),
            dt.datetime.combine(end_day + dt.timedelta(days=1), dt.time.min),
        )
        return events, active.label

    events, label = _cached(
        ("upcoming", offset, days, start_day), config.CALENDAR_CACHE_SECONDS, produce
    )
    if events is None:
        return None, None
    return group_by_day(events, start_day, end_day), label
