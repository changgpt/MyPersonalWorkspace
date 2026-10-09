"""Adding a project directly, and the task form's inline "+"."""
from daybook import db


def test_add_a_project_from_the_list_page(client, app):
    response = client.post("/projects/new", data={"name": "Hedging book"})
    assert response.status_code == 302
    with app.app_context():
        projects = db.list_projects()
    assert [p["name"] for p in projects] == ["Hedging book"]
    # Straight to the project, the way People goes straight to the person.
    assert response.headers["Location"].endswith(f"/projects/{projects[0]['id']}")


def test_adding_an_existing_name_opens_it_rather_than_duplicating(client, app):
    with app.app_context():
        existing = db.find_or_create_project("Hedging book")
    # Same case-insensitive find-or-create the note tag field uses.
    response = client.post("/projects/new", data={"name": "hedging BOOK"})
    with app.app_context():
        assert len(db.list_projects()) == 1
    assert response.headers["Location"].endswith(f"/projects/{existing}")


def test_a_blank_name_creates_nothing(client, app):
    client.post("/projects/new", data={"name": "   "})
    with app.app_context():
        assert db.list_projects() == []


def test_the_json_variant_is_what_the_inline_button_uses(client, app):
    """The task form's "+" creates a project without navigating away, so it
    needs the new row back rather than a redirect to its page."""
    response = client.post(
        "/projects/new", data={"name": "Vol surface"}, headers={"Accept": "application/json"}
    )
    assert response.status_code == 200
    assert response.get_json()["name"] == "Vol surface"
    with app.app_context():
        assert db.get_project(response.get_json()["id"])["name"] == "Vol surface"


def test_the_task_form_offers_the_inline_add(client, app):
    body = client.get("/tasks/new").get_data(as_text=True)
    assert 'data-add-project="/projects/new"' in body
    assert 'data-target-select="project_id"' in body


def test_the_projects_page_offers_the_inline_add(client, app):
    body = client.get("/projects").get_data(as_text=True)
    assert 'action="/projects/new"' in body
