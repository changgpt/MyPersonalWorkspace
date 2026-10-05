import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "daybook.db"

# Phase 4 (off by default): AI features only turn on if a key is present
# AND the in-app Settings toggle is switched on.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-local-single-user")
