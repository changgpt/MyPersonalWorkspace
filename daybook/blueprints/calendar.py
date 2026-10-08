"""The Dashboard's "Coming up" card.

Its own blueprint rather than part of `dashboard.py` because it's loaded
*separately* from the page: reading Outlook takes a few hundred
milliseconds at best, and the Dashboard is the first thing you see, so
making it wait would undo the whole point of the htmx work. The card
arrives via `hx-trigger="load"` and the arrows swap the same fragment --
the usual partial pattern, except there's no full-page variant to serve,
since "Coming up" only ever exists inside the Dashboard.
"""
import click
from flask import Blueprint, render_template, request

from .. import calendar_sources, calendar_utils

bp = Blueprint("calendar", __name__, url_prefix="/calendar")


@bp.route("/upcoming")
def upcoming_view():
    offset = request.args.get("offset", default=0, type=int)
    days, source_label, error, hint = None, None, None, None
    try:
        days, source_label = calendar_utils.upcoming(offset)
        if days is None:
            hint = calendar_sources.unavailable_hint()
    except calendar_sources.CalendarError as exc:
        # Shown in the card, not flashed: a calendar that can't be reached
        # is a property of that card, and a toast on every Dashboard load
        # would be unbearable.
        error = str(exc)
    return render_template(
        "calendar/_upcoming.html",
        days=days,
        source_label=source_label,
        error=error,
        hint=hint,
        offset=offset,
    )


@click.command("outlook-login")
def outlook_login_command():
    """Sign in to Microsoft Graph once, for the Dashboard's Coming up card.

    Only needed on the Graph path -- the Outlook desktop (COM) source needs
    no sign-in at all. Prints a code to type into a browser, then writes a
    token cache to data/ that the app refreshes silently from then on.
    """
    source = calendar_sources.GraphSource()
    try:
        source.sign_in(echo=click.echo)
    except calendar_sources.CalendarError as exc:
        raise click.ClickException(str(exc))
    calendar_utils.clear_cache()
    click.echo("Signed in. The Dashboard's Coming up card will use Microsoft Graph.")


@click.command("outlook-check")
def outlook_check_command():
    """Say why the Dashboard's Coming up card isn't showing anything.

    Exists because the card can only show one short line, and the actual
    cause is usually an environment fact the user can't see from the
    browser (pywin32 missing, OUTLOOK_SOURCE pinned, no token yet). Prints
    counts only -- never event subjects -- so it's safe to paste.
    """
    import sys

    from .. import config

    click.echo(f"platform          : {sys.platform}")
    click.echo(f"OUTLOOK_SOURCE    : {config.OUTLOOK_SOURCE}")
    com = calendar_sources.OutlookComSource()
    graph = calendar_sources.GraphSource()
    click.echo(f"pywin32 importable: {com.is_available()}")
    click.echo(f"GRAPH_CLIENT_ID   : {'set' if config.GRAPH_CLIENT_ID else 'not set'}")
    click.echo(f"graph signed in   : {graph.is_available()}")

    try:
        source = calendar_sources.resolve_source()
    except calendar_sources.CalendarError as exc:
        click.echo(f"\nresolved source   : none -- {exc}")
        return
    if source is None:
        click.echo(f"\nresolved source   : none")
        click.echo(calendar_sources.unavailable_hint())
        return

    click.echo(f"\nresolved source   : {source.label}")
    calendar_utils.clear_cache()
    try:
        days, label = calendar_utils.upcoming(0)
    except calendar_sources.CalendarError as exc:
        click.echo(f"reading it failed : {exc}")
        return
    for day in days or []:
        click.echo(f"  {day['date']:%a %d %b}: {len(day['events'])} event(s)")
    click.echo("OK -- the card should show this.")
