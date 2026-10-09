from datetime import datetime

from daybook import greetings


def test_greeting_for_hour_covers_morning_afternoon_evening_and_late_night():
    assert greetings.greeting_for_hour(8)[0] == "Good morning"
    assert greetings.greeting_for_hour(14)[0] == "Good afternoon"
    assert greetings.greeting_for_hour(19)[0] == "Good evening"
    assert greetings.greeting_for_hour(2)[0] == "Burning the midnight oil"
    assert greetings.greeting_for_hour(23)[0] == "Burning the midnight oil"


def test_greeting_message_includes_name_when_given():
    now = datetime(2026, 1, 1, 9, 0)
    assert greetings.greeting_message("Thess", now=now) == "Good morning, Thess ☀️"


def test_greeting_message_omits_trailing_comma_when_name_is_blank():
    now = datetime(2026, 1, 1, 9, 0)
    message = greetings.greeting_message("", now=now)
    assert message == "Good morning ☀️"
    assert "," not in message


def test_random_quote_returns_text_and_author():
    quote = greetings.random_quote()
    assert quote["text"]
    assert quote["author"]


def test_greeting_parts_keep_the_emoji_apart_for_the_dashboard_mark():
    # The Dashboard sets the emoji *before* the words as a mark, so it
    # needs them separately; the no-name/no-comma rule must still hold.
    now = datetime(2026, 10, 9, 9, 0)
    assert greetings.greeting_parts("Thess", now=now) == ("Good morning, Thess", "☀️")
    words, _ = greetings.greeting_parts("  ", now=now)
    assert words == "Good morning"


def test_dashboard_renders_the_mark_before_the_words(client):
    # Whatever the hour, the mark is the heading's first child.
    body = client.get("/").get_data(as_text=True)
    assert '<h1 class="greeting-text"><span class="greeting-mark"' in body


def test_fonts_are_vendored_not_fetched(client):
    """Both faces ship with the app (OFL, static/vendor/fonts) -- the same
    never-from-a-CDN rule htmx and Turndown follow."""
    css = client.get("/static/style.css").get_data(as_text=True)
    assert 'url("vendor/fonts/Inter.woff2")' in css
    assert 'url("vendor/fonts/Newsreader.woff2")' in css
    assert "fonts.googleapis" not in css and "fonts.gstatic" not in css
    for name in ("Inter.woff2", "Newsreader.woff2"):
        assert client.get(f"/static/vendor/fonts/{name}").status_code == 200
