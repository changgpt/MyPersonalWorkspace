"""Reading upcoming events out of Outlook, for the Dashboard's "Coming up".

This module is the *only* place that touches COM or the network -- the same
split as `ai.py`, so everything downstream (grouping, formatting, the
"Take notes" prefill) is pure and testable without a live Outlook. The two
functions that convert a provider's event into our own `CalendarEvent`
(`event_from_com_item` / `event_from_graph`) are deliberately pure too:
they take a plain object/dict, so `tests/test_calendar_sources.py` can
exercise them against captured payload shapes.

Two sources, because the right one depends on the machine:

- `OutlookComSource` talks to a *classic* Outlook desktop install over COM.
  It needs no credentials at all -- it reads the profile you're already
  signed into -- which is what makes it the zero-setup option on a managed
  work laptop. It can't work on the "new Outlook" app (no COM interface)
  or on any non-Windows machine.
- `GraphSource` calls Microsoft Graph with a delegated token obtained once
  by `flask outlook-login` (device code) and refreshed silently after that.
  It works anywhere, including new Outlook, but needs an app registration.

`resolve_source()` picks: whatever `OUTLOOK_SOURCE` names, or the first
available one. A missing/broken source is never an error here -- it returns
`None` (or raises `CalendarError`, which the blueprint shows as a one-line
hint) so the Dashboard still renders.
"""
import datetime as dt
import json
import sys
from dataclasses import dataclass, field

from . import config

GRAPH_SCOPES = ["Calendars.Read"]
GRAPH_ROOT = "https://graph.microsoft.com/v1.0"

# Outlook's calendar folder, as an olDefaultFolders constant. Spelled out
# rather than imported so this module doesn't need the COM enums present.
_OL_FOLDER_CALENDAR = 9


def _require_msal():
    """msal is optional (see requirements.txt), and the web path never gets
    here because `is_available()` returns False without it. `flask
    outlook-login` calls straight in though, so turn the ImportError into
    something that says what to install."""
    try:
        import msal
    except ImportError as exc:
        raise CalendarError(
            "The Microsoft Graph calendar path needs msal: pip install -r requirements.txt"
        ) from exc
    return msal


class CalendarError(Exception):
    """A source was asked for events and couldn't deliver them.

    Carries a message meant to be read by the user (shown in the "Coming
    up" card), so it should say what to do, not just what broke.
    """


@dataclass
class CalendarEvent:
    """One occurrence, normalised across both sources.

    `start`/`end` are **naive local** datetimes. Both sources are asked for
    local times at the boundary -- COM hands back local by nature, and
    Graph is sent a `Prefer: outlook.timezone` header -- so nothing
    downstream has to carry a timezone or do DST arithmetic. An all-day
    event still gets a start/end (midnight to midnight), but `is_all_day`
    is what templates should branch on rather than inspecting the times.
    """

    subject: str
    start: dt.datetime
    end: dt.datetime
    is_all_day: bool = False
    location: str = ""
    organizer: str = ""
    join_url: str = ""
    web_link: str = ""
    show_as: str = ""
    attendees: list = field(default_factory=list)  # display names, self excluded

    @property
    def day(self):
        return self.start.date()

    def ends_after(self, moment):
        """Used to drop meetings that have already finished from *today*,
        so "Coming up" means coming up rather than a log of the morning."""
        return self.end > moment


def _clean(value):
    return (value or "").strip()


# --- Microsoft Graph ---------------------------------------------------

def event_from_graph(payload, self_email=""):
    """Convert one Graph `event` resource into a `CalendarEvent`.

    Pure: `payload` is the parsed JSON dict, so this is tested directly
    against a captured Graph response rather than through the network.
    """
    def _dt(part):
        # Graph returns 7-digit fractional seconds, which fromisoformat
        # rejected before 3.11; trimming is simpler than version-gating.
        raw = (payload.get(part) or {}).get("dateTime", "")
        raw = raw[:26] if "." in raw else raw
        return dt.datetime.fromisoformat(raw) if raw else None

    start, end = _dt("start"), _dt("end")
    if start is None or end is None:
        return None

    self_email = self_email.lower()
    attendees = []
    for attendee in payload.get("attendees") or []:
        email = (attendee.get("emailAddress") or {})
        address = _clean(email.get("address")).lower()
        if address and address == self_email:
            continue
        name = _clean(email.get("name")) or address
        if name:
            attendees.append(name)

    return CalendarEvent(
        subject=_clean(payload.get("subject")) or "(no subject)",
        start=start,
        end=end,
        is_all_day=bool(payload.get("isAllDay")),
        location=_clean((payload.get("location") or {}).get("displayName")),
        organizer=_clean(
            ((payload.get("organizer") or {}).get("emailAddress") or {}).get("name")
        ),
        join_url=_clean((payload.get("onlineMeeting") or {}).get("joinUrl")),
        web_link=_clean(payload.get("webLink")),
        show_as=_clean(payload.get("showAs")),
        attendees=attendees,
    )


class GraphSource:
    """Delegated Microsoft Graph access, refreshed silently.

    The device-code prompt lives in `flask outlook-login`, not here: a web
    request can't sensibly block for 60 seconds while someone types a code
    into a browser, so the CLI does that once and leaves a token cache
    behind. This class only ever calls `acquire_token_silent`, and says
    "run flask outlook-login" if that comes back empty.
    """

    name = "graph"
    label = "Microsoft Graph"

    def __init__(self):
        self._self_email = ""

    # -- auth

    def _cache_path(self):
        return config.DATA_DIR / "graph_token_cache.json"

    def _msal_app(self, cache=None):
        msal = _require_msal()
        return msal.PublicClientApplication(
            config.GRAPH_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{config.GRAPH_TENANT_ID}",
            token_cache=cache,
        )

    def _load_cache(self):
        cache = _require_msal().SerializableTokenCache()
        path = self._cache_path()
        if path.exists():
            cache.deserialize(path.read_text(encoding="utf-8"))
        return cache

    def _save_cache(self, cache):
        if cache.has_state_changed:
            path = self._cache_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(cache.serialize(), encoding="utf-8")
            # The cache holds a refresh token, so keep it owner-only. Best
            # effort: Windows ignores the mode, and the file already sits in
            # the git-ignored data/ directory.
            try:
                path.chmod(0o600)
            except OSError:
                pass

    def is_available(self):
        try:
            import msal  # noqa: F401
        except ImportError:
            return False
        return bool(config.GRAPH_CLIENT_ID) and self._cache_path().exists()

    def _token(self):
        if not config.GRAPH_CLIENT_ID:
            raise CalendarError(
                "Microsoft Graph isn't configured yet -- set GRAPH_CLIENT_ID "
                "in .env, then run `flask outlook-login`."
            )
        cache = self._load_cache()
        app = self._msal_app(cache)
        accounts = app.get_accounts()
        result = app.acquire_token_silent(GRAPH_SCOPES, account=accounts[0]) if accounts else None
        self._save_cache(cache)
        if not result or "access_token" not in result:
            raise CalendarError("Outlook sign-in has expired -- run `flask outlook-login` again.")
        return result["access_token"]

    def sign_in(self, echo=print):
        """Device-code flow, called by `flask outlook-login`. Prints the
        code and blocks until the browser side completes."""
        _require_msal()
        if not config.GRAPH_CLIENT_ID:
            raise CalendarError("Set GRAPH_CLIENT_ID (and GRAPH_TENANT_ID) in .env first.")
        cache = self._load_cache()
        app = self._msal_app(cache)
        flow = app.initiate_device_flow(scopes=GRAPH_SCOPES)
        if "user_code" not in flow:
            raise CalendarError(
                "Microsoft refused to start the sign-in: "
                f"{flow.get('error_description', flow)}"
            )
        echo(flow["message"])
        result = app.acquire_token_by_device_flow(flow)
        self._save_cache(cache)
        if "access_token" not in result:
            raise CalendarError(result.get("error_description", "Sign-in failed."))
        return result

    # -- fetching

    def _get(self, path, token, params=None, timezone=None):
        import requests

        headers = {"Authorization": f"Bearer {token}"}
        if timezone:
            # Asks Graph to return start/end already converted, so we never
            # do DST arithmetic ourselves. The quoting is required.
            headers["Prefer"] = f'outlook.timezone="{timezone}"'
        response = requests.get(
            f"{GRAPH_ROOT}{path}", headers=headers, params=params, timeout=20
        )
        if response.status_code == 403:
            raise CalendarError(
                "Microsoft Graph refused the request (403) -- the app registration "
                "is probably missing delegated Calendars.Read consent."
            )
        if not response.ok:
            raise CalendarError(f"Microsoft Graph returned {response.status_code}.")
        return response.json()

    def _resolve_self_email(self, token):
        if self._self_email:
            return self._self_email
        try:
            me = self._get("/me", token, params={"$select": "mail,userPrincipalName"})
            self._self_email = _clean(me.get("mail") or me.get("userPrincipalName"))
        except CalendarError:
            self._self_email = ""  # only used to drop yourself from attendees
        return self._self_email

    def fetch(self, start, end):
        token = self._token()
        self_email = self._resolve_self_email(token)
        payload = self._get(
            "/me/calendarView",
            token,
            params={
                "startDateTime": start.isoformat(),
                "endDateTime": end.isoformat(),
                "$select": "subject,start,end,isAllDay,isCancelled,showAs,location,"
                           "organizer,onlineMeeting,webLink,attendees",
                "$orderby": "start/dateTime",
                "$top": "100",
            },
            timezone=config.CALENDAR_TIMEZONE,
        )
        events = []
        for item in payload.get("value", []):
            if item.get("isCancelled"):
                continue
            event = event_from_graph(item, self_email)
            if event:
                events.append(event)
        return events


# --- Classic Outlook desktop over COM ---------------------------------

def event_from_com_item(item, self_email=""):
    """Convert one Outlook `AppointmentItem` into a `CalendarEvent`.

    Takes anything with the COM item's attribute names, so the tests feed
    it a stub -- this file can't be exercised against real COM anywhere but
    a Windows box with classic Outlook installed.
    """
    start, end = getattr(item, "Start", None), getattr(item, "End", None)
    if start is None or end is None:
        return None
    # pywin32 hands back its own time type; it behaves like a datetime but
    # isn't one, so normalise before anything downstream compares it.
    start = dt.datetime.fromtimestamp(start.timestamp()) if hasattr(start, "timestamp") else start
    end = dt.datetime.fromtimestamp(end.timestamp()) if hasattr(end, "timestamp") else end

    self_email = self_email.lower()
    attendees = []
    # RequiredAttendees/OptionalAttendees are semicolon-separated display
    # names. Recipients would give addresses too, but walking it fires a
    # COM call per recipient and is noticeably slow over a slow profile.
    raw = ";".join(
        filter(None, [
            _clean(getattr(item, "RequiredAttendees", "")),
            _clean(getattr(item, "OptionalAttendees", "")),
        ])
    )
    for name in raw.split(";"):
        name = _clean(name)
        if name and name.lower() != self_email:
            attendees.append(name)

    # OlBusyStatus: 0 free, 1 tentative, 2 busy, 3 out of office, 4 working
    # elsewhere. Mapped to Graph's vocabulary so templates only know one.
    busy_status = getattr(item, "BusyStatus", None)
    show_as = {0: "free", 1: "tentative", 2: "busy", 3: "oof", 4: "workingElsewhere"}.get(
        busy_status, ""
    )

    return CalendarEvent(
        subject=_clean(getattr(item, "Subject", "")) or "(no subject)",
        start=start,
        end=end,
        is_all_day=bool(getattr(item, "AllDayEvent", False)),
        location=_clean(getattr(item, "Location", "")),
        organizer=_clean(getattr(item, "Organizer", "")),
        # Outlook has no "join URL" property; the Teams link lives in the
        # body. Left empty rather than scraped -- a wrong link is worse
        # than none, and the event still opens in Outlook via web_link.
        join_url="",
        web_link="",
        show_as=show_as,
        attendees=attendees,
    )


class OutlookComSource:
    name = "com"
    label = "Outlook desktop"

    def import_error(self):
        """`None` if `win32com.client` imports, else the ImportError.

        The *reason* matters and used to be discarded. pywin32 has two
        quite different failure modes that need opposite fixes, and both
        raise ImportError: "No module named 'win32com'" means it isn't
        installed in *this* interpreter, while "DLL load failed" means it
        is installed but its native extensions aren't registered. Telling
        someone to reinstall when it's already installed sends them in
        circles, so the message is kept and shown.
        """
        try:
            import win32com.client  # noqa: F401
        except ImportError as exc:
            return exc
        return None

    def is_available(self):
        return self.import_error() is None

    def fetch(self, start, end):
        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:  # pragma: no cover - Windows-only path
            raise CalendarError("Outlook desktop access needs pywin32 installed.") from exc

        # Flask serves each request on a worker thread, and COM has to be
        # initialised per thread or Dispatch fails with CO_E_NOTINITIALIZED.
        pythoncom.CoInitialize()
        try:
            namespace = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
            self_email = ""
            try:
                self_email = _clean(namespace.CurrentUser.Address)
            except Exception:  # pragma: no cover - profile without an address
                pass

            items = namespace.GetDefaultFolder(_OL_FOLDER_CALENDAR).Items
            # Order matters and is the classic trap here: recurrences only
            # expand if IncludeRecurrences is set *and* the collection is
            # sorted by Start *before* Restrict runs. Get it wrong and every
            # recurring meeting -- i.e. most of them -- silently vanishes.
            items.IncludeRecurrences = True
            items.Sort("[Start]")
            # Restrict wants US-format dates regardless of locale.
            fmt = "%m/%d/%Y %I:%M %p"
            items = items.Restrict(
                f"[Start] < '{end.strftime(fmt)}' AND [End] > '{start.strftime(fmt)}'"
            )

            events = []
            for item in items:
                try:
                    event = event_from_com_item(item, self_email)
                except Exception:  # pragma: no cover - one odd item mustn't kill the card
                    continue
                if event:
                    events.append(event)
            return events
        except CalendarError:
            raise
        except Exception as exc:  # pragma: no cover - Windows-only path
            raise CalendarError(
                "Couldn't reach Outlook desktop. It needs classic Outlook running "
                f"on this machine (the new Outlook app has no COM interface). {exc}"
            ) from exc
        finally:
            pythoncom.CoUninitialize()


# --- Source selection -------------------------------------------------

_SOURCES = {cls.name: cls for cls in (OutlookComSource, GraphSource)}


def unavailable_hint(preference=None):
    """Why no source is available, phrased as what to do about it.

    The card used to show one generic line here, which actively misled on
    the most likely case: on Windows the COM source reports itself
    unavailable when `pywin32` simply isn't installed, and "it works with
    no setup" is a lie in exactly that situation. Each branch below names
    the one next step for the machine it's actually running on.
    """
    preference = (preference or config.OUTLOOK_SOURCE or "auto").lower()
    if preference == "off":
        return "Calendar is switched off (OUTLOOK_SOURCE=off in .env)."

    on_windows = sys.platform == "win32"
    com = OutlookComSource()
    com_error = com.import_error()

    if on_windows and com_error is not None:
        if isinstance(com_error, ModuleNotFoundError):
            # `python -m pip`, not bare `pip`: installing into a different
            # interpreter than the one running the app is the usual reason
            # a package "installed fine" and still isn't importable.
            return (
                "Outlook desktop needs the pywin32 package, which isn't installed in "
                "the Python running this app. Run `python -m pip install -r "
                "requirements.txt` (that exact form, so it installs into this same "
                "Python), then restart `python run.py`. `flask outlook-check` prints "
                "which interpreter that is."
            )
        # Installed but not loadable -- almost always the post-install step
        # that registers pywin32's DLLs, which pip can't run unelevated.
        return (
            f"pywin32 is installed but won't load ({com_error}). This is usually its "
            "post-install step: run `python -m pywin32_postinstall -install` in an "
            "Administrator terminal, then restart `python run.py`."
        )
    if on_windows and com_error is None:
        # is_available() is true, so resolve_source() wouldn't have given
        # up -- reachable only if OUTLOOK_SOURCE pins the other source.
        return (
            "Outlook desktop is available but OUTLOOK_SOURCE is set to "
            f"'{preference}'. Set OUTLOOK_SOURCE=auto in .env to use it."
        )

    # Not Windows, so COM is off the table and Graph is the only option.
    if not config.GRAPH_CLIENT_ID:
        return (
            "Outlook desktop needs Windows, so this machine has to use Microsoft "
            "Graph: set GRAPH_CLIENT_ID in .env (see .env.example), then run "
            "`flask outlook-login`."
        )
    return "Almost there -- run `flask outlook-login` to finish connecting to Outlook."


def resolve_source(preference=None):
    """The source to use, or None if the feature isn't set up.

    `OUTLOOK_SOURCE=com|graph` forces one (and then an unavailable source
    raises, so a typo in .env is visible rather than silently falling
    through); `auto` tries desktop Outlook first, since it needs no
    credentials, then Graph. `off` disables the card entirely.
    """
    preference = (preference or config.OUTLOOK_SOURCE or "auto").lower()
    if preference == "off":
        return None
    if preference in _SOURCES:
        source = _SOURCES[preference]()
        if not source.is_available():
            raise CalendarError(
                f"OUTLOOK_SOURCE={preference} is set but {source.label} isn't available here."
            )
        return source
    for cls in (OutlookComSource, GraphSource):
        source = cls()
        if source.is_available():
            return source
    return None
