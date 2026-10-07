"""Helpers for views that answer both a full page load and an htmx swap.

Every list page here is a plain GET with its filters in the query string,
which means one route can serve both: the browser gets the whole page,
htmx gets just the fragment it asked to swap. Keeping both on the same
route (rather than adding /notes/fragment endpoints) is what lets the
filtered URL stay shareable, bookmarkable and reload-safe.
"""
from flask import request


def is_htmx():
    """True when htmx issued this request (it sets HX-Request on all of
    them), i.e. the caller wants a fragment rather than a whole page."""
    return request.headers.get("HX-Request") == "true"


def template_for(full_page, fragment):
    """The template to render for this request: the fragment for an htmx
    swap, the full page otherwise. The fragment is always also `include`d
    by the full page, so the two can't drift apart."""
    return fragment if is_htmx() else full_page
