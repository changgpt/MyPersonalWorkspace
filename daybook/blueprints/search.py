from flask import Blueprint, render_template, request, url_for

from .. import db

bp = Blueprint("search", __name__, url_prefix="/search")

# Longest prefix wins, so "/weekly-review" isn't matched by "/w..." and
# "/" only matches when nothing else does. Used to label the results
# page's Back link with where you actually came from ("Back to Tasks"
# rather than a bare "Back").
_SECTION_LABELS = (
    ("/notes", "Notes"),
    ("/tasks", "Tasks"),
    ("/topics", "Knowledge Bank"),
    ("/people", "People"),
    ("/projects", "Projects"),
    ("/activity", "Activity Log"),
    ("/skills", "Skills"),
    ("/wins", "Wins"),
    ("/weekly-review", "Weekly Review"),
    ("/settings", "Settings"),
    ("/", "Dashboard"),
)


def _back_target():
    """(url, label) for the Back link. The search box threads the page it
    was used from through as `from`; only an internal path is honored (the
    same rule as tasks._safe_next -- an absolute URL here would be an open
    redirect), and anything else falls back to the Dashboard."""
    # request.full_path (what the search box sends) always ends in "?",
    # even with no query string -- harmless but ugly in the address bar.
    path = request.args.get("from", "").rstrip("?")
    if not path.startswith("/"):
        return url_for("dashboard.index"), "Dashboard"
    for prefix, label in _SECTION_LABELS:
        if path.startswith(prefix):
            return path, label
    return path, "Back"


@bp.route("")
def search_view():
    query_text = request.args.get("q", "")
    results = db.search_notes(query_text) if query_text.strip() else []
    back_url, back_label = _back_target()
    return render_template(
        "search/results.html",
        query_text=query_text,
        results=results,
        back_url=back_url,
        back_label=back_label,
    )


@bp.route("/suggest")
def suggest_view():
    """The typeahead dropdown under the global search box.

    Deliberately its own endpoint rather than an HX-Request branch on
    search_view (the usual convention here): this isn't the results page
    in fragment form, it's a different, shorter thing -- capped per kind,
    spanning tasks/people/projects/topics as well as notes, and rendered
    over whatever page you're already on. An empty query renders nothing
    at all, which is what closes the dropdown (CSS hides it when empty).
    """
    query_text = request.args.get("q", "")
    return render_template(
        "search/_suggestions.html",
        query_text=query_text,
        groups=db.search_suggestions(query_text),
        from_path=request.args.get("from", ""),
    )
