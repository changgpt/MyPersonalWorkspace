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
