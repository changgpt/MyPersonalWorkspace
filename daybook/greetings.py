"""Dashboard greeting: a time-of-day salutation plus a motivational quote.

Pure presentation, no persistence and no network call (contrast with
ai.py's actual API-backed features) -- just the local machine's clock
(this is a single-user, 127.0.0.1-only app, so server time is the user's
own time) and a hardcoded quote list.
"""
import random
from datetime import datetime

# (start hour, end hour inclusive, greeting, emoji). Anything outside all
# three ranges (21:00-04:59) falls through to _LATE_NIGHT below.
_PERIODS = (
    (5, 11, "Good morning", "☀️"),
    (12, 16, "Good afternoon", "\U0001f324️"),
    (17, 20, "Good evening", "\U0001f306"),
)
_LATE_NIGHT = ("Burning the midnight oil", "\U0001f319")

QUOTES = [
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("It always seems impossible until it's done.", "Nelson Mandela"),
    ("The way to get started is to quit talking and begin doing.", "Walt Disney"),
    ("Success is not final, failure is not fatal: it is the courage to "
     "continue that counts.", "Winston Churchill"),
    ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ("Well done is better than well said.", "Benjamin Franklin"),
    ("The future depends on what you do today.", "Mahatma Gandhi"),
    ("You miss 100% of the shots you don't take.", "Wayne Gretzky"),
    ("It does not matter how slowly you go as long as you do not stop.", "Confucius"),
    ("Energy and persistence conquer all things.", "Benjamin Franklin"),
    ("Whether you think you can or you think you can't, you're right.", "Henry Ford"),
    ("Opportunities don't happen. You create them.", "Chris Grosser"),
    ("Don't watch the clock; do what it does. Keep going.", "Sam Levenson"),
    ("Little by little, one travels far.", "J.R.R. Tolkien"),
    ("The best way to predict the future is to create it.", "Peter Drucker"),
    ("Act as if what you do makes a difference. It does.", "William James"),
    ("A year from now you may wish you had started today.", "Karen Lamb"),
    ("Discipline is the bridge between goals and accomplishment.", "Jim Rohn"),
    ("Start where you are. Use what you have. Do what you can.", "Arthur Ashe"),
    ("The only limit to our realization of tomorrow is our doubts of today.",
     "Franklin D. Roosevelt"),
    ("What we think, we become.", "Buddha"),
    ("Do not wait to strike till the iron is hot; but make it hot by striking.",
     "William Butler Yeats"),
    ("A year of good decisions starts with one good hour.", "Unknown"),
]


def greeting_for_hour(hour):
    """(text, emoji) for a given 0-23 hour, e.g. (\"Good morning\", \"...\")."""
    for start, end, text, emoji in _PERIODS:
        if start <= hour <= end:
            return text, emoji
    return _LATE_NIGHT


def greeting_message(display_name, now=None):
    text, emoji = greeting_for_hour((now or datetime.now()).hour)
    name = (display_name or "").strip()
    return f"{text}, {name} {emoji}" if name else f"{text} {emoji}"


def random_quote():
    text, author = random.choice(QUOTES)
    return {"text": text, "author": author}
