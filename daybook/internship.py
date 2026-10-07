"""Internship countdown + week tracker shown on the Dashboard.

Pure date arithmetic, no persistence -- mirrors greetings.py (presentation
helper, no DB or network call). Start/end dates come from config (read
from .env), not stored anywhere, since they never change during a run.
"""
from datetime import date


def week_number(start_date, today=None):
    """1-indexed week number since start_date (week 1 is the first 7 days,
    inclusive of the start date itself). Clamped to 1 if today is before
    start_date (e.g. the date is set up ahead of the actual start)."""
    today = today or date.today()
    days_in = (today - start_date).days
    if days_in < 0:
        return 1
    return (days_in // 7) + 1


def days_remaining(end_date, today=None):
    """Days left until end_date (0 on end_date itself). Clamped to 0 once
    end_date has passed."""
    today = today or date.today()
    return max((end_date - today).days, 0)
