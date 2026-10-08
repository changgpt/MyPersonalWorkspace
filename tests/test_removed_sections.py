"""Activity log and Wins were removed from the UI, not from the database.

Deliberately reversible: the `win`/`win_person`/`log_entry` tables, their
`db.py` functions and their place in the export are all untouched, so
nothing a user already recorded is lost and the pages could come back.
These tests pin both halves of that -- the routes are gone, the data is
not.
"""
import pytest

from daybook import db as db_module


@pytest.mark.parametrize("path", [
    "/activity", "/activity/new", "/wins", "/wins/new", "/wins/1",
])
def test_removed_pages_are_gone(client, path):
    assert client.get(path).status_code == 404


def test_nav_no_longer_offers_them(client):
    body = client.get("/").get_data(as_text=True)
    assert "Activity Log" not in body
    assert ">Wins<" not in body


def test_dashboard_drops_completed_this_week(client, db):
    db_module.create_task(title="Done thing", bucket="today")
    task_id = db_module.list_tasks()[0]["id"]
    db_module.set_task_status(task_id, "done")
    body = client.get("/").get_data(as_text=True)
    assert "Completed this week" not in body
    # The query itself still exists (the weekly review uses it); it's only
    # off the Dashboard.
    assert db_module.list_tasks_completed_this_week()


def test_dashboard_still_shows_overdue_separately(client, db):
    # Overdue has to keep its own section: dashboard.index filters overdue
    # ids out of the today list, so without it an overdue task would
    # disappear from the page rather than merely be listed twice.
    db_module.create_task(title="Reconcile Q3", bucket="today", due_date="2000-01-01")
    body = client.get("/").get_data(as_text=True)
    assert "Overdue" in body
    assert body.count("Reconcile Q3") == 1


def test_dashboard_button_says_quick_note(client):
    body = client.get("/").get_data(as_text=True)
    assert "Quick note" in body
    assert "+ New note" not in body


def test_task_form_no_longer_offers_mark_as_win(client, db):
    db_module.create_task(title="Shipped it", bucket="today")
    task_id = db_module.list_tasks()[0]["id"]
    db_module.set_task_status(task_id, "done")
    body = client.get(f"/tasks/{task_id}/edit").get_data(as_text=True)
    assert "Mark as win" not in body


def test_the_data_and_its_export_survive(client, db):
    # The whole point of removing only the UI.
    win_id = db_module.create_win("2026-10-07", "Shipped the model")
    db_module.create_log_entry(entry_date="2026-10-07", description="Paired on the model")
    assert db_module.get_win(win_id)["title"] == "Shipped the model"

    import io, json, zipfile
    payload = client.get("/settings/export").data
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        data = json.loads(archive.read("data.json"))
    assert [w["title"] for w in data["wins"]] == ["Shipped the model"]
    assert [l["description"] for l in data["log_entries"]] == ["Paired on the model"]


def test_weekly_review_no_longer_shows_a_wins_section(client, db):
    db_module.create_win("2026-10-07", "Shipped the model")
    body = client.get("/weekly-review").get_data(as_text=True)
    assert "Shipped the model" not in body


def test_skill_evidence_pointing_at_a_win_renders_without_a_dead_link(client, db):
    # Evidence recorded before the removal still resolves to a title; it
    # just isn't a link any more.
    skill_id = db_module.create_skill("Modelling")
    win_id = db_module.create_win("2026-10-07", "Shipped the model")
    db_module.add_skill_evidence("Modelling", "win", win_id, "built it")
    response = client.get(f"/skills/{skill_id}")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Shipped the model" in body
    assert "/wins/" not in body
