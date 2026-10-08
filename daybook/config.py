import os
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "daybook.db"

# Phase 4 (off by default): AI features only turn on if a key is present
# AND the in-app Settings toggle is switched on.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5-5")

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-local-single-user")

# Shown on the Dashboard's "Good morning, <name>" greeting. Empty by default
# so a brand-new install doesn't greet you by someone else's name.
DISPLAY_NAME = os.environ.get("DISPLAY_NAME", "")


def _parse_date(value, default):
    """.env stores dates as plain YYYY-MM-DD strings; fall back to the
    hardcoded default rather than crashing the app if one is malformed."""
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default


# Dashboard's internship countdown + "Week N" tracker. Both overridable in
# .env (YYYY-MM-DD) -- the end date is a real hardcoded default since it's
# fixed and known; the start date defaults to today only as a last resort,
# since that's a guess, not a real fallback value.
INTERNSHIP_START_DATE = _parse_date(os.environ.get("INTERNSHIP_START_DATE"), date(2026, 10, 5))
INTERNSHIP_END_DATE = _parse_date(os.environ.get("INTERNSHIP_END_DATE"), date(2027, 4, 2))


# --- Outlook "Coming up" card -----------------------------------------
# Which source reads the calendar: "auto" (classic Outlook desktop over
# COM if it's there, else Microsoft Graph), "com", "graph", or "off" to
# hide the card. See daybook/calendar_sources.py.
OUTLOOK_SOURCE = os.environ.get("OUTLOOK_SOURCE", "auto")

# Graph path only. The client id of a public-client app registration with
# delegated Calendars.Read; no client secret is involved (and none should
# be put here) because the token is yours, obtained by `flask
# outlook-login`. Tenant defaults to "organizations" so a work account
# works without knowing the tenant id.
GRAPH_CLIENT_ID = os.environ.get("GRAPH_CLIENT_ID", "")
GRAPH_TENANT_ID = os.environ.get("GRAPH_TENANT_ID", "organizations")

# Windows timezone name (not an IANA one): this is what Graph's
# `Prefer: outlook.timezone` header expects, and it's also exactly what
# Outlook reports as your mailbox timezone, so it can be copied straight
# from there. Only used on the Graph path -- COM is already local.
CALENDAR_TIMEZONE = os.environ.get("CALENDAR_TIMEZONE", "GMT Standard Time")

# How many days the card shows at once, and how far the arrows page.
CALENDAR_DAYS = int(os.environ.get("CALENDAR_DAYS", "3") or 3)

# Short on purpose: long enough that paging the arrows back and forth is
# instant, short enough that a meeting just accepted shows up on its own.
CALENDAR_CACHE_SECONDS = int(os.environ.get("CALENDAR_CACHE_SECONDS", "120") or 120)
