"""Deleting the five tag-like entities, and what survives it.

The point of every test here is the *other* row: deleting a person must
not take her notes with her, deleting a project must not take its tasks.
Both are only true because of a deliberate choice -- ON DELETE CASCADE on
the join tables, and `delete_project` nulling the FKs that have no ON
DELETE action at all -- so each is pinned rather than assumed.
"""
from daybook import db


def _note(title="A note", type_id=1, **tags):
    return db.create_note(
        title=title,
        note_type_id=type_id,
        event_date="2026-10-07",
        body_markdown="body",
        **tags,
    )


# --- People ---------------------------------------------------------------

def test_deleting_a_person_keeps_their_notes(client, app):
    with app.app_context():
        person_id = db.find_or_create_person("Ada")
        note_id = _note("1:1 with Ada", person_ids=[person_id])

    assert client.post(f"/people/{person_id}/delete").status_code == 302

    with app.app_context():
        assert db.get_person(person_id) is None
        # The note is the record; the tag was only an index into it.
        assert db.get_note(note_id) is not None
        assert db.notes_for_person(person_id) == []


def test_deleting_a_missing_person_is_a_404(client, app):
    assert client.post("/people/999/delete").status_code == 404


# --- Projects -------------------------------------------------------------

def test_deleting_a_project_unfiles_its_tasks(client, app):
    # task.project_id references project(id) with *no* ON DELETE action, so
    # without delete_project's UPDATE first this would fail the FK outright.
    with app.app_context():
        project_id = db.find_or_create_project("Hedging")
        task_id = db.create_task("Model the book", project_id=project_id)
        note_id = _note("Hedging kickoff", project_ids=[project_id])

    assert client.post(f"/projects/{project_id}/delete").status_code == 302

    with app.app_context():
        assert db.get_project(project_id) is None
        task = db.get_task(task_id)
        assert task is not None
        assert task["project_id"] is None
        assert db.get_note(note_id) is not None


# --- Topics ---------------------------------------------------------------

def test_deleting_a_topic_keeps_its_notes(client, app):
    with app.app_context():
        topic_id = db.find_or_create_topic("Convexity")
        note_id = _note("Convexity reading", topic_ids=[topic_id])

    assert client.post(f"/topics/{topic_id}/delete").status_code == 302

    with app.app_context():
        assert db.get_topic(topic_id) is None
        assert db.get_note(note_id) is not None


# --- Skills ---------------------------------------------------------------

def test_deleting_a_skill_takes_its_history_and_evidence_only(client, app):
    with app.app_context():
        note_id = _note("Where I used it")
        db.add_skill_evidence("Python", "note", note_id)
        skill_id = db.find_or_create_skill("Python")
        db.update_skill(skill_id, "Python", "technical", "", 3)
        assert db.skill_level_history(skill_id)
        assert db.evidence_for_entity("note", note_id)

    assert client.post(f"/skills/{skill_id}/delete").status_code == 302

    with app.app_context():
        assert db.get_skill(skill_id) is None
        assert db.skill_level_history(skill_id) == []
        # Only the *link* went -- the note it pointed at is untouched.
        assert db.evidence_for_entity("note", note_id) == []
        assert db.get_note(note_id) is not None


# --- Note types -----------------------------------------------------------

def test_a_note_type_in_use_cannot_be_deleted(client, app):
    with app.app_context():
        type_id = db.create_note_type("Standup", "sage", "")
        _note("Monday standup", type_id=type_id)

    response = client.post(f"/settings/note-types/{type_id}/delete",
                           follow_redirects=True)
    assert response.status_code == 200
    # Refused with the alternative named, rather than cascading or 500ing:
    # note.note_type_id is NOT NULL, so there's nowhere to put the note.
    assert "Archive it instead" in response.get_data(as_text=True)
    with app.app_context():
        assert db.get_note_type(type_id) is not None


def test_an_unused_note_type_can_be_deleted(client, app):
    with app.app_context():
        type_id = db.create_note_type("Standup", "sage", "")

    assert client.post(f"/settings/note-types/{type_id}/delete").status_code == 302
    with app.app_context():
        assert db.get_note_type(type_id) is None


# --- The delete controls are actually reachable ---------------------------

def test_every_entity_offers_a_delete_somewhere(client, app):
    """A db function nothing links to is not a feature."""
    with app.app_context():
        person_id = db.find_or_create_person("Ada")
        project_id = db.find_or_create_project("Hedging")
        topic_id = db.find_or_create_topic("Convexity")
        skill_id = db.find_or_create_skill("Python")
        task_id = db.create_task("Model the book")
        type_id = db.create_note_type("Standup", "sage", "")

    pages = {
        f"/people/{person_id}/edit": f"/people/{person_id}/delete",
        f"/projects/{project_id}": f"/projects/{project_id}/delete",
        f"/topics/{topic_id}": f"/topics/{topic_id}/delete",
        f"/skills/{skill_id}/edit": f"/skills/{skill_id}/delete",
        f"/tasks/{task_id}/edit": f"/tasks/{task_id}/delete",
        f"/settings/note-types/{type_id}/edit":
            f"/settings/note-types/{type_id}/delete",
    }
    for page, action in pages.items():
        body = client.get(page).get_data(as_text=True)
        assert action in body, page


def test_delete_forms_are_never_nested_in_another_form(client, app):
    """HTML forbids it and browsers silently drop the inner <form>, so the
    button would render and then do nothing at all."""
    with app.app_context():
        person_id = db.find_or_create_person("Ada")
        skill_id = db.find_or_create_skill("Python")
        task_id = db.create_task("Model the book")
        type_id = db.create_note_type("Standup", "sage", "")

    for page in (
        f"/people/{person_id}/edit",
        f"/skills/{skill_id}/edit",
        f"/tasks/{task_id}/edit",
        f"/settings/note-types/{type_id}/edit",
    ):
        body = client.get(page).get_data(as_text=True)
        depth = 0
        for fragment in body.split("<form")[1:]:
            assert depth == 0, f"nested <form> on {page}"
            depth += 1
            depth -= fragment.count("</form>")
        assert depth == 0, page
