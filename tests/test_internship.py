from datetime import date

from daybook import internship


def test_week_number_starts_at_1_on_start_date():
    start = date(2026, 10, 5)
    assert internship.week_number(start, today=date(2026, 10, 5)) == 1
    assert internship.week_number(start, today=date(2026, 10, 11)) == 1
    assert internship.week_number(start, today=date(2026, 10, 12)) == 2
    assert internship.week_number(start, today=date(2026, 10, 19)) == 3


def test_week_number_clamps_to_1_before_start_date():
    start = date(2026, 10, 5)
    assert internship.week_number(start, today=date(2026, 9, 1)) == 1


def test_days_remaining_counts_down_to_zero():
    end = date(2027, 4, 2)
    assert internship.days_remaining(end, today=date(2027, 4, 1)) == 1
    assert internship.days_remaining(end, today=date(2027, 4, 2)) == 0


def test_days_remaining_clamps_to_zero_after_end_date():
    end = date(2027, 4, 2)
    assert internship.days_remaining(end, today=date(2027, 5, 1)) == 0
