"""The "Coming up" card's pure layer.

The two `event_from_*` converters and all the grouping are deliberately
free of COM/network calls (see daybook/calendar_sources.py), which is what
lets this file cover them without a live Outlook. The Graph payloads below
are real response shapes with the names and subjects replaced -- the point
is the structure Graph actually returns (7-digit fractional seconds,
`isAllDay`, `isCancelled`, nested `emailAddress`, `onlineMeeting: null`),
since that's what the converter has to survive.
"""
import datetime as dt
import types

import pytest

from daybook import calendar_sources as cs
from daybook import calendar_utils as cu

SELF = "tchang@capdyn.com"


def graph_event(**overrides):
    payload = {
        "subject": "CE PDS Weekly",
        "isAllDay": False,
        "isCancelled": False,
        "showAs": "busy",
        "webLink": "https://outlook.office365.com/owa/?itemid=AAA",
        "start": {"dateTime": "2026-10-09T11:30:00.0000000", "timeZone": "GMT Standard Time"},
        "end": {"dateTime": "2026-10-09T12:00:00.0000000", "timeZone": "GMT Standard Time"},
        "location": {"displayName": "Microsoft Teams Meeting", "locationType": "default"},
        "organizer": {"emailAddress": {"name": "Dana Okafor", "address": "dokafor@example.com"}},
        "onlineMeeting": {"joinUrl": "https://teams.microsoft.com/l/meetup-join/19%3ameeting_X"},
        "attendees": [
            {"emailAddress": {"name": "Dana Okafor", "address": "dokafor@example.com"}},
            {"emailAddress": {"name": "Thess Chang", "address": SELF}},
        ],
    }
    payload.update(overrides)
    return payload


# --- Graph conversion -------------------------------------------------

def test_graph_event_is_normalised():
    event = cs.event_from_graph(graph_event(), SELF)
    assert event.subject == "CE PDS Weekly"
    assert event.start == dt.datetime(2026, 10, 9, 11, 30)
    assert event.end == dt.datetime(2026, 10, 9, 12, 0)
    assert event.is_all_day is False
    assert event.location == "Microsoft Teams Meeting"
    assert event.organizer == "Dana Okafor"
    assert event.join_url.startswith("https://teams.microsoft.com/")
    assert event.show_as == "busy"


def test_graph_seven_digit_fractional_seconds_parse():
    # Graph returns 7 digits of fractional seconds, which is more than
    # fromisoformat accepted before 3.11 -- the converter trims them.
    event = cs.event_from_graph(graph_event(), SELF)
    assert event.start.microsecond == 0


def test_graph_attendees_exclude_yourself():
    event = cs.event_from_graph(graph_event(), SELF)
    assert event.attendees == ["Dana Okafor"]


def test_graph_attendee_match_is_case_insensitive():
    payload = graph_event(attendees=[
        {"emailAddress": {"name": "Thess Chang", "address": SELF.upper()}},
        {"emailAddress": {"name": "Sam Ito", "address": "sito@example.com"}},
    ])
    assert cs.event_from_graph(payload, SELF).attendees == ["Sam Ito"]


def test_graph_all_day_event():
    payload = graph_event(
        subject="Capital call notice",
        isAllDay=True,
        showAs="free",
        onlineMeeting=None,
        location={"displayName": ""},
        start={"dateTime": "2026-10-08T00:00:00.0000000", "timeZone": "UTC"},
        end={"dateTime": "2026-10-09T00:00:00.0000000", "timeZone": "UTC"},
    )
    event = cs.event_from_graph(payload, SELF)
    assert event.is_all_day is True
    assert event.join_url == ""
    assert event.location == ""
    assert cu.format_time_range(event) == "All day"


def test_graph_event_missing_times_is_skipped():
    assert cs.event_from_graph(graph_event(start={}, end={}), SELF) is None


def test_graph_event_without_subject_still_renders():
    assert cs.event_from_graph(graph_event(subject=""), SELF).subject == "(no subject)"


# --- COM conversion ---------------------------------------------------
# Duck-typed stand-in for an Outlook AppointmentItem: the converter only
# reads attributes, so this covers it on a machine with no Outlook.

def com_item(**overrides):
    attrs = dict(
        Subject="Project Tanit - Final IC",
        Start=dt.datetime(2026, 10, 9, 15, 0),
        End=dt.datetime(2026, 10, 9, 16, 0),
        AllDayEvent=False,
        Location="Boardroom",
        Organizer="Dana Okafor",
        BusyStatus=2,
        RequiredAttendees="Dana Okafor; Thess Chang",
        OptionalAttendees="Sam Ito",
    )
    attrs.update(overrides)
    return types.SimpleNamespace(**attrs)


def test_com_item_is_normalised():
    event = cs.event_from_com_item(com_item(), "Thess Chang")
    assert event.subject == "Project Tanit - Final IC"
    assert event.start == dt.datetime(2026, 10, 9, 15, 0)
    assert event.location == "Boardroom"
    assert event.show_as == "busy"
    # Required and optional attendees are one semicolon-separated string
    # each; both are split and you are dropped from the result.
    assert event.attendees == ["Dana Okafor", "Sam Ito"]


def test_com_busy_status_maps_to_graph_vocabulary():
    # Templates should only ever have to know one set of names.
    assert cs.event_from_com_item(com_item(BusyStatus=0), "").show_as == "free"
    assert cs.event_from_com_item(com_item(BusyStatus=1), "").show_as == "tentative"
    assert cs.event_from_com_item(com_item(BusyStatus=3), "").show_as == "oof"
    assert cs.event_from_com_item(com_item(BusyStatus=None), "").show_as == ""


def test_com_item_without_times_is_skipped():
    assert cs.event_from_com_item(com_item(Start=None), "") is None


# --- The day window ---------------------------------------------------

def test_day_window_starts_at_today():
    today = dt.date(2026, 10, 8)
    start, end = cu.day_window(offset=0, days=3, today=today)
    assert (start, end) == (today, dt.date(2026, 10, 11))


def test_day_window_pages_by_whole_windows():
    # The arrows should move a screenful, not a day.
    today = dt.date(2026, 10, 8)
    assert cu.day_window(1, 3, today) == (dt.date(2026, 10, 11), dt.date(2026, 10, 14))
    assert cu.day_window(-1, 3, today) == (dt.date(2026, 10, 5), dt.date(2026, 10, 8))


# --- Grouping ---------------------------------------------------------

def event(subject, start, end, **kwargs):
    return cs.CalendarEvent(subject=subject, start=start, end=end, **kwargs)


def test_group_by_day_keeps_empty_days():
    now = dt.datetime(2026, 10, 8, 9, 0)
    days = cu.group_by_day(
        [event("Later today", dt.datetime(2026, 10, 8, 14, 0), dt.datetime(2026, 10, 8, 15, 0))],
        dt.date(2026, 10, 8), dt.date(2026, 10, 11), now=now,
    )
    assert [d["date"].day for d in days] == [8, 9, 10]
    assert len(days[0]["events"]) == 1
    assert days[1]["events"] == []


def test_finished_events_drop_off_today_only():
    now = dt.datetime(2026, 10, 8, 12, 0)
    events = [
        event("This morning", dt.datetime(2026, 10, 8, 9, 0), dt.datetime(2026, 10, 8, 9, 30)),
        event("In progress", dt.datetime(2026, 10, 8, 11, 30), dt.datetime(2026, 10, 8, 12, 30)),
        event("This afternoon", dt.datetime(2026, 10, 8, 16, 0), dt.datetime(2026, 10, 8, 17, 0)),
    ]
    days = cu.group_by_day(events, dt.date(2026, 10, 8), dt.date(2026, 10, 9), now=now)
    titles = [e.subject for e in days[0]["events"]]
    # A meeting still running counts as coming up; one that ended doesn't.
    assert titles == ["In progress", "This afternoon"]


def test_past_days_keep_their_finished_events():
    # Reachable with the back arrow, where "coming up" doesn't apply.
    now = dt.datetime(2026, 10, 8, 12, 0)
    events = [event("Yesterday", dt.datetime(2026, 10, 7, 9, 0), dt.datetime(2026, 10, 7, 9, 30))]
    days = cu.group_by_day(events, dt.date(2026, 10, 7), dt.date(2026, 10, 8), now=now)
    assert [e.subject for e in days[0]["events"]] == ["Yesterday"]
    assert days[0]["is_past"] is True


def test_all_day_event_stays_on_today_even_once_started():
    now = dt.datetime(2026, 10, 8, 17, 0)
    events = [event(
        "Capital call notice",
        dt.datetime(2026, 10, 8, 0, 0), dt.datetime(2026, 10, 9, 0, 0), is_all_day=True,
    )]
    days = cu.group_by_day(events, dt.date(2026, 10, 8), dt.date(2026, 10, 9), now=now)
    assert len(days[0]["events"]) == 1


def test_all_day_events_sort_above_timed_ones():
    now = dt.datetime(2026, 10, 9, 8, 0)
    events = [
        event("Standup", dt.datetime(2026, 10, 10, 9, 30), dt.datetime(2026, 10, 10, 10, 0)),
        event("Offsite", dt.datetime(2026, 10, 10, 0, 0), dt.datetime(2026, 10, 11, 0, 0),
              is_all_day=True),
    ]
    days = cu.group_by_day(events, dt.date(2026, 10, 10), dt.date(2026, 10, 11), now=now)
    assert [e.subject for e in days[0]["events"]] == ["Offsite", "Standup"]


def test_today_and_other_days_get_different_empty_labels():
    now = dt.datetime(2026, 10, 8, 18, 0)
    days = cu.group_by_day([], dt.date(2026, 10, 8), dt.date(2026, 10, 10), now=now)
    assert days[0]["empty_label"] == "No more events today"
    assert days[0]["is_today"] is True
    assert days[1]["empty_label"] == "Nothing scheduled"


# --- Formatting + the note prefill ------------------------------------

def test_time_range_is_24_hour():
    e = event("x", dt.datetime(2026, 10, 9, 13, 0), dt.datetime(2026, 10, 9, 13, 30))
    assert cu.format_time_range(e) == "13:00 - 13:30"


def test_note_prefill_carries_title_date_and_people():
    e = event(
        "David / Thessabel",
        dt.datetime(2026, 10, 9, 11, 30), dt.datetime(2026, 10, 9, 12, 0),
        attendees=["David Osei"],
    )
    assert cu.note_prefill(e) == {
        "title": "David / Thessabel",
        "date": "2026-10-09",
        "people": "David Osei",
    }


def test_note_prefill_omits_people_when_there_are_none():
    e = event("Focus block", dt.datetime(2026, 10, 9, 9, 0), dt.datetime(2026, 10, 9, 10, 0))
    assert "people" not in cu.note_prefill(e)


# --- Source selection -------------------------------------------------

def test_source_off_disables_the_card():
    assert cs.resolve_source("off") is None


def test_explicit_source_that_is_unavailable_raises():
    # A typo'd or impossible OUTLOOK_SOURCE should be visible, not silently
    # fall through to the other source.
    with pytest.raises(cs.CalendarError) as excinfo:
        cs.resolve_source("com" if not cs.OutlookComSource().is_available() else "graph")
    assert "isn't available" in str(excinfo.value)


def test_auto_returns_none_when_nothing_is_configured(monkeypatch):
    monkeypatch.setattr(cs.OutlookComSource, "is_available", lambda self: False)
    monkeypatch.setattr(cs.GraphSource, "is_available", lambda self: False)
    assert cs.resolve_source("auto") is None


# --- The route --------------------------------------------------------

class StubSource:
    label = "Stub"

    def __init__(self, events=(), error=None):
        self._events, self._error = list(events), error

    def is_available(self):
        return True

    def fetch(self, start, end):
        if self._error:
            raise cs.CalendarError(self._error)
        return self._events


@pytest.fixture(autouse=True)
def _no_cache_between_tests():
    cu.clear_cache()
    yield
    cu.clear_cache()


def test_upcoming_route_renders_events(client, monkeypatch):
    today = dt.date.today()
    at = dt.datetime.combine(today, dt.time(23, 30))
    monkeypatch.setattr(
        cs, "resolve_source",
        lambda preference=None: StubSource([
            event("CE PDS Weekly", at, at + dt.timedelta(minutes=30), attendees=["Dana Okafor"]),
        ]),
    )
    body = client.get("/calendar/upcoming").get_data(as_text=True)
    assert "CE PDS Weekly" in body
    assert "23:30 - 00:00" in body
    # The note link carries the prefill, so "Take notes" lands on a note
    # that's already about this meeting.
    assert "/notes/new?" in body and "Dana+Okafor" in body


def test_upcoming_route_shows_a_setup_hint_when_unconfigured(client, monkeypatch):
    monkeypatch.setattr(cs, "resolve_source", lambda preference=None: None)
    body = client.get("/calendar/upcoming").get_data(as_text=True)
    assert "Not connected to Outlook yet" in body


def test_upcoming_route_shows_the_error_instead_of_failing(client, monkeypatch):
    monkeypatch.setattr(
        cs, "resolve_source",
        lambda preference=None: StubSource(error="Outlook isn't running."),
    )
    response = client.get("/calendar/upcoming")
    # The card reports it; the request must still succeed, or a broken
    # calendar would take the whole Dashboard down with it.
    assert response.status_code == 200
    assert "Outlook isn&#39;t running." in response.get_data(as_text=True)


def test_dashboard_renders_without_touching_the_calendar(client, monkeypatch):
    def explode(preference=None):
        raise AssertionError("the Dashboard must not read the calendar inline")

    monkeypatch.setattr(cs, "resolve_source", explode)
    body = client.get("/").get_data(as_text=True)
    # The card is fetched afterwards by htmx, so the page itself only
    # carries the placeholder.
    assert 'hx-get="/calendar/upcoming"' in body
    assert "Checking your calendar" in body


def test_offset_pages_the_window(client, monkeypatch):
    monkeypatch.setattr(cs, "resolve_source", lambda preference=None: StubSource([]))
    body = client.get("/calendar/upcoming?offset=1").get_data(as_text=True)
    expected = dt.date.today() + dt.timedelta(days=3)
    assert str(expected.day) in body
    # Paged away from today, so a way back is offered.
    assert "Back to today" in body


def test_results_are_cached_between_requests(client, monkeypatch):
    calls = []

    class Counting(StubSource):
        def fetch(self, start, end):
            calls.append((start, end))
            return []

    monkeypatch.setattr(cs, "resolve_source", lambda preference=None: Counting())
    client.get("/calendar/upcoming")
    client.get("/calendar/upcoming")
    assert len(calls) == 1, "the second load should have come from cache"


def test_note_prefill_skips_people_for_a_large_meeting():
    # A distribution-list notice would otherwise create a Person row per
    # recipient on one careless save.
    many = [f"Person {n}" for n in range(cu.MAX_PREFILL_PEOPLE + 1)]
    e = event("All-hands", dt.datetime(2026, 10, 9, 9, 0), dt.datetime(2026, 10, 9, 10, 0),
              attendees=many)
    assert "people" not in cu.note_prefill(e)
    assert cu.note_prefill(e)["title"] == "All-hands"


def test_note_prefill_keeps_people_at_the_limit():
    some = [f"Person {n}" for n in range(cu.MAX_PREFILL_PEOPLE)]
    e = event("Team sync", dt.datetime(2026, 10, 9, 9, 0), dt.datetime(2026, 10, 9, 10, 0),
              attendees=some)
    assert cu.note_prefill(e)["people"].count(",") == cu.MAX_PREFILL_PEOPLE - 1


def test_missing_msal_reports_what_to_install(monkeypatch):
    # `flask outlook-login` calls straight into the Graph source, bypassing
    # the is_available() guard the web path goes through, so a missing
    # optional dependency has to surface as advice rather than a traceback.
    import builtins

    real_import = builtins.__import__

    def no_msal(name, *args, **kwargs):
        if name == "msal":
            raise ImportError("no msal")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_msal)
    with pytest.raises(cs.CalendarError) as excinfo:
        cs.GraphSource().sign_in()
    assert "pip install" in str(excinfo.value)


def test_graph_is_unavailable_without_a_client_id(monkeypatch):
    monkeypatch.setattr(cs.config, "GRAPH_CLIENT_ID", "")
    assert cs.GraphSource().is_available() is False
