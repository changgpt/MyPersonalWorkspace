"""Every form in the app wears the same compose layout.

The user's ask was literally "the exact same" as the note form: a faded
"New XX" placeholder standing in for the page heading, rounded pills
instead of labelled boxes, and no page <h2>. That's a cross-cutting
convention, so it's pinned in one place -- otherwise the next form added
quietly goes back to labels and boxes.
"""
from daybook import db

# (path, the placeholder that stands in for the heading)
COMPOSE_PAGES = [
    ("/notes/new", "New note"),
    ("/tasks/new", "New task"),
    ("/skills/new", "New skill"),
    ("/settings/note-types/new", "New note type"),
]


def _existing_pages(app):
    """The two compose screens that only exist for a row that's already
    there (there's no /people/new form -- see CLAUDE.md)."""
    with app.app_context():
        person_id = db.find_or_create_person("Ada")
        skill_id = db.find_or_create_skill("Python")
        task_id = db.create_task("Model the book")
        type_id = db.create_note_type("Standup", "sage", "")
    return [
        f"/people/{person_id}/edit",
        f"/skills/{skill_id}/edit",
        f"/tasks/{task_id}/edit",
        f"/settings/note-types/{type_id}/edit",
    ]


def test_new_forms_put_the_heading_in_the_title_placeholder(client, app):
    for path, placeholder in COMPOSE_PAGES:
        body = client.get(path).get_data(as_text=True)
        assert 'class="compose"' in body, path
        assert f'placeholder="{placeholder}"' in body, path
        assert "compose-title" in body, path


def test_no_compose_screen_has_a_page_heading(client, app):
    # The point of the faded placeholder is that it *is* the heading --
    # a page-header above it would say the same thing twice.
    for path, _ in COMPOSE_PAGES:
        assert "page-header" not in client.get(path).get_data(as_text=True), path
    for path in _existing_pages(app):
        assert "page-header" not in client.get(path).get_data(as_text=True), path


def test_every_compose_screen_uses_pills_not_labelled_boxes(client, app):
    for path, _ in COMPOSE_PAGES:
        body = client.get(path).get_data(as_text=True)
        assert "compose-meta" in body, path
        # Either a joined group (notes) or standalone pills (everything
        # else), but never a bare labelled <select>.
        assert ("compose-pills" in body) or ("compose-pill" in body), path


def test_compose_screens_keep_their_real_fields(client, app):
    """The layout is cosmetic; every field the route reads must still post."""
    expected = {
        "/tasks/new": ["name=\"title\"", "name=\"priority\"", "name=\"bucket\"",
                       "name=\"project_id\"", "name=\"due_date\"",
                       "name=\"description\""],
        "/skills/new": ["name=\"name\"", "name=\"category\"", "name=\"level\"",
                        "name=\"notes\""],
        "/settings/note-types/new": ["name=\"name\"", "name=\"color\"",
                                     "name=\"template_markdown\""],
    }
    for path, fields in expected.items():
        body = client.get(path).get_data(as_text=True)
        for field in fields:
            assert field in body, (path, field)


def test_the_people_form_still_posts_every_crm_field(client, app):
    with app.app_context():
        person_id = db.find_or_create_person("Ada")
    body = client.get(f"/people/{person_id}/edit").get_data(as_text=True)
    for field in ("name", "role", "team", "last_contacted_date", "how_met",
                  "context", "follow_up"):
        assert f'name="{field}"' in body, field

    client.post(f"/people/{person_id}", data={
        "name": "Ada Lovelace", "role": "Quant", "team": "Rates",
        "how_met": "Onboarding", "context": "Owns the curve model",
        "last_contacted_date": "2026-10-06", "follow_up": "Send the deck",
    })
    with app.app_context():
        person = db.get_person(person_id)
    assert person["name"] == "Ada Lovelace"
    assert person["role"] == "Quant"
    assert person["notes"] == "Owns the curve model"
    assert person["last_contacted_date"] == "2026-10-06"
    assert person["follow_up"] == "Send the deck"


def test_optional_date_pills_read_as_words_not_iso(client, app):
    """The same date chip as a note's, so "Today"/"Never" reads the same
    everywhere -- and the real <input type="date"> is still behind it."""
    with app.app_context():
        person_id = db.find_or_create_person("Ada")
        task_id = db.create_task("Model the book")

    task_body = client.get(f"/tasks/{task_id}/edit").get_data(as_text=True)
    assert "data-date-chip" in task_body
    # The empty label matches what date-chip.js renders client-side, so
    # the first paint doesn't flash a different word.
    assert "Pick a date</button>" in task_body
    assert 'type="date" id="due_date" name="due_date"' in task_body

    person_body = client.get(f"/people/{person_id}/edit").get_data(as_text=True)
    assert "Pick a date</button>" in person_body
    assert 'name="last_contacted_date"' in person_body


def test_the_sidebar_search_advertises_its_shortcut(client, app):
    body = client.get("/").get_data(as_text=True)
    sidebar, _, _ = body.partition('<main class="main">')
    assert "search-icon" in sidebar
    assert "Ctrl K" in sidebar
    # The Back-link origin still rides along; without it the results page
    # has nothing to offer a "Back to Tasks" link from.
    assert 'name="from"' in sidebar
