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
