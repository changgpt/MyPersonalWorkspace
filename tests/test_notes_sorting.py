"""The Notes list groups by note type by default.

A flat reverse-chronological wall of cards has no structure to scan; "all
the 1:1s, then all the meetings" does. Newest-first is still one click
away, so both orders are pinned here.
"""
from daybook import db as db_module
from daybook.blueprints.notes import _group_by_type


def _three_notes():
    types = {nt["name"]: nt["id"] for nt in db_module.list_note_types()}
    names = sorted(types)
    # Two of one type, one of another, with dates that would interleave
    # them under a pure date sort -- so the two orderings differ visibly.
    db_module.create_note("Older A", types[names[0]], "2026-10-01", "")
    db_module.create_note("Middle B", types[names[1]], "2026-10-05", "")
    db_module.create_note("Newer A", types[names[0]], "2026-10-09", "")


def test_default_sort_groups_by_type_then_newest_within_each(app):
    with app.app_context():
        _three_notes()
        notes = db_module.list_notes()
        groups = _group_by_type(notes)

    # One group per type, in alphabetical type order.
    assert [g[0] for g in groups] == sorted({n["type_name"] for n in notes})
    # Newest first inside a group.
    first = groups[0]
    assert [n["title"] for n in first[2]] == ["Newer A", "Older A"]
    # Every note lands in exactly one group.
    assert sum(len(g[2]) for g in groups) == len(notes)


def test_date_sort_is_still_available_and_ignores_type(app):
    with app.app_context():
        _three_notes()
        titles = [n["title"] for n in db_module.list_notes(sort="date")]
    assert titles == ["Newer A", "Middle B", "Older A"]


def test_unknown_sort_falls_back_rather_than_erroring(app):
    # The sort value reaches the SQL, so an unrecognised one must not be
    # interpolated or raise -- it's a query string the user can type.
    with app.app_context():
        _three_notes()
        assert db_module.list_notes(sort="'; DROP TABLE note; --") == db_module.list_notes()
        assert db_module.list_notes(sort=None) == db_module.list_notes()


def test_list_page_renders_a_type_heading_per_group(client, app):
    with app.app_context():
        _three_notes()
        names = sorted({nt["name"] for nt in db_module.list_note_types()})[:2]
    body = client.get("/notes").get_data(as_text=True)
    assert "note-group-heading" in body
    for name in names:
        assert name in body


def test_sort_by_date_renders_one_flat_grid(client, app):
    with app.app_context():
        _three_notes()
    body = client.get("/notes?sort=date").get_data(as_text=True)
    # No group headings, and the sort control remembers the choice.
    assert "note-group-heading" not in body
    assert 'value="date" selected' in body


def test_grouping_survives_a_filter(client, app):
    with app.app_context():
        _three_notes()
        type_id = sorted(db_module.list_note_types(), key=lambda r: r["name"])[0]["id"]
    body = client.get(f"/notes?type={type_id}").get_data(as_text=True)
    assert "note-group-heading" in body
    assert "Middle B" not in body


def test_grouped_cards_do_not_repeat_the_type_tag(client, app):
    # The group heading already names the type; a tag on every card as
    # well was the noisiest thing on the page.
    with app.app_context():
        _three_notes()
    grouped = client.get("/notes").get_data(as_text=True)
    flat = client.get("/notes?sort=date").get_data(as_text=True)
    # One tag per group heading when grouped, one per card when flat.
    assert grouped.count('class="tag tag-') < flat.count('class="tag tag-')


def test_search_lives_in_the_sidebar_not_over_the_content(client, app):
    # It used to sit on top of every page, which made it noise on the
    # screens you write on. It's now one field in the nav column, so it's
    # present everywhere but never part of the page itself.
    for path in ("/notes/new", "/notes", "/", "/weekly-review", "/settings/note-types"):
        body = client.get(path, follow_redirects=True).get_data(as_text=True)
        assert "global-search" in body, path
        sidebar, _, main = body.partition('<main class="main">')
        assert "global-search" in sidebar, path
        assert "global-search" not in main, path


def test_compose_date_renders_as_a_friendly_chip(client, app):
    body = client.get("/notes/new").get_data(as_text=True)
    assert "data-date-chip" in body
    # The label is server-rendered through the same human_date filter the
    # rest of the app uses, so the first paint is right before JS runs.
    assert "Today</button>" in body
    # ...and the real input is still there, named and required.
    assert 'type="date" id="event_date" name="event_date" required' in body
