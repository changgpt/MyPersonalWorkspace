from datetime import date, datetime

from daybook import date_utils

TODAY = date(2026, 10, 7)


def test_relative_days_read_as_words():
    assert date_utils.human_date("2026-10-07", today=TODAY) == "Today"
    assert date_utils.human_date("2026-10-06", today=TODAY) == "Yesterday"
    assert date_utils.human_date("2026-10-08", today=TODAY) == "Tomorrow"


def test_surrounding_week_keeps_the_date_alongside_the_weekday():
    # A bare "Monday" would be ambiguous between last and next week.
    assert date_utils.human_date("2026-10-05", today=TODAY) == "Mon 5 Oct"
    assert date_utils.human_date("2026-10-12", today=TODAY) == "Mon 12 Oct"


def test_same_year_drops_the_year_and_other_years_keep_it():
    assert date_utils.human_date("2026-03-01", today=TODAY) == "1 Mar"
    assert date_utils.human_date("2025-12-24", today=TODAY) == "24 Dec 2025"


def test_accepts_timestamps_dates_and_datetimes():
    assert date_utils.human_date("2026-10-07T14:30:00+00:00", today=TODAY) == "Today"
    assert date_utils.human_date(date(2026, 10, 7), today=TODAY) == "Today"
    assert date_utils.human_date(datetime(2026, 10, 7, 9, 0), today=TODAY) == "Today"


def test_unparseable_values_pass_through_rather_than_raising():
    assert date_utils.human_date(None, today=TODAY) == ""
    assert date_utils.human_date("", today=TODAY) == ""
    assert date_utils.human_date("not a date", today=TODAY) == "not a date"


def test_week_range_marks_the_current_week():
    assert date_utils.human_date_range("2026-10-05", "2026-10-11", today=TODAY) == \
        "This week · 5 - 11 Oct"
    assert date_utils.human_date_range("2026-10-12", "2026-10-18", today=TODAY) == "12 - 18 Oct"


def test_week_range_spanning_two_months_names_both():
    assert date_utils.human_date_range("2026-09-28", "2026-10-04", today=TODAY) == "28 Sep - 4 Oct"


def test_week_range_in_another_year_keeps_the_year():
    assert date_utils.human_date_range("2025-10-06", "2025-10-12", today=TODAY) == "6 - 12 Oct 2025"
