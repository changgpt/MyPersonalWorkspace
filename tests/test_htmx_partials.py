"""Every page that htmx swaps must still answer a plain request with the
whole page -- that's what keeps a filtered URL reload-safe and shareable.
These pin both halves of each dual-response view.
"""
from daybook import db as db_module

HX = {"HX-Request": "true"}


def _make_note(client, db, title="A note"):
    note_type = db_module.list_note_types()[0]
    return db_module.create_note(
        title=title, note_type_id=note_type["id"],
        event_date="2026-01-01", body_markdown="body",
    )


def test_notes_list_returns_full_page_normally_and_fragment_for_htmx(client, db):
    _make_note(client, db)

    full = client.get("/notes").get_data(as_text=True)
    assert "<!DOCTYPE html>" in full
    assert 'id="notes-results"' in full

    fragment = client.get("/notes", headers=HX).get_data(as_text=True)
    assert "<!DOCTYPE html>" not in fragment
    assert 'id="notes-results"' in fragment


def test_board_returns_full_page_normally_and_fragment_for_htmx(client, db):
    db_module.create_task(title="A task")

    assert "<!DOCTYPE html>" in client.get("/tasks/board").get_data(as_text=True)
    fragment = client.get("/tasks/board", headers=HX).get_data(as_text=True)
    assert "<!DOCTYPE html>" not in fragment
    assert 'id="board-columns"' in fragment


def test_today_returns_full_page_normally_and_fragment_for_htmx(client, db):
    db_module.create_task(title="A task", bucket="today")

    assert "<!DOCTYPE html>" in client.get("/tasks").get_data(as_text=True)
    fragment = client.get("/tasks", headers=HX).get_data(as_text=True)
    assert "<!DOCTYPE html>" not in fragment
    assert 'id="today-checklists"' in fragment


def test_quick_add_redirects_without_htmx_but_swaps_checklists_with_it(client, db):
    plain = client.post("/tasks", data={"title": "Typed with no JS"})
    assert plain.status_code == 302
    assert plain.headers["Location"] == "/tasks"

    swapped = client.post("/tasks", data={"title": "Typed with htmx"}, headers=HX)
    assert swapped.status_code == 200
    body = swapped.get_data(as_text=True)
    assert 'id="today-checklists"' in body
    # The new task is in the markup htmx is about to swap in, so the list
    # updates without a reload.
    assert "Typed with htmx" in body
    assert {t["title"] for t in db_module.list_tasks()} == {"Typed with no JS", "Typed with htmx"}



def test_weekly_review_save_returns_204_for_htmx_and_redirects_otherwise(client, db):
    data = {"went_well": "Shipped it", "to_improve": "", "focus_next_week": ""}

    plain = client.post("/weekly-review/2026-W01", data=data)
    assert plain.status_code == 302

    swapped = client.post("/weekly-review/2026-W01", data=data, headers=HX)
    assert swapped.status_code == 204
    assert db_module.get_weekly_review("2026-W01")["went_well"] == "Shipped it"
