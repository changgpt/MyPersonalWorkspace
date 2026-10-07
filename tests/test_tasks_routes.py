from daybook import db as db_module


def test_update_redirects_back_to_next_page(client, db):
    task_id = db_module.create_task(title="Original title")

    response = client.post(
        f"/tasks/{task_id}?next=/notes/1",
        data={"title": "Updated title", "priority": "medium"},
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/notes/1"
    assert db_module.get_task(task_id)["title"] == "Updated title"


def test_delete_redirects_back_to_next_page(client, db):
    task_id = db_module.create_task(title="To delete")

    response = client.post(f"/tasks/{task_id}/delete?next=/projects/3")
    assert response.status_code == 302
    assert response.headers["Location"] == "/projects/3"
    assert db_module.get_task(task_id) is None


def test_update_without_next_falls_back_to_today_view(client, db):
    task_id = db_module.create_task(title="Original title")

    response = client.post(f"/tasks/{task_id}", data={"title": "Updated", "priority": "low"})
    assert response.headers["Location"] == "/tasks"


def test_next_rejects_external_url(client, db):
    task_id = db_module.create_task(title="Original title")

    response = client.post(
        f"/tasks/{task_id}?next=https://evil.example.com",
        data={"title": "Updated", "priority": "low"},
    )
    assert response.headers["Location"] == "/tasks"


def test_edit_view_passes_next_through_to_form(client, db):
    task_id = db_module.create_task(title="A task")

    response = client.get(f"/tasks/{task_id}/edit?next=/notes/7")
    body = response.get_data(as_text=True)
    assert f'/tasks/{task_id}?next=/notes/7' in body
    assert f'/tasks/{task_id}/delete?next=/notes/7' in body


def test_toggle_uses_hx_current_url_for_edit_link(client, db):
    task_id = db_module.create_task(title="A task")

    response = client.post(
        f"/tasks/{task_id}/toggle",
        headers={"HX-Current-URL": "http://localhost/notes/9"},
    )
    body = response.get_data(as_text=True)
    assert f'/tasks/{task_id}/edit?next=/notes/9' in body


def test_new_task_form_creates_and_redirects_to_next(client, db):
    response = client.post(
        "/tasks/new?next=/tasks/board",
        data={"title": "Brand new task", "priority": "high", "bucket": "long_term"},
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/tasks/board"

    task = db_module.list_tasks()[0]
    assert task["title"] == "Brand new task"
    assert task["bucket"] == "long_term"


def test_move_updates_bucket(client, db):
    task_id = db_module.create_task(title="Movable", bucket="today")

    response = client.post(f"/tasks/{task_id}/move", data={"bucket": "background"})
    assert response.status_code == 204
    assert db_module.get_task(task_id)["bucket"] == "background"


def test_move_updates_status_and_reopens_when_dragged_off_done(client, db):
    task_id = db_module.create_task(title="Finish me", bucket="long_term")
    db_module.set_task_status(task_id, "done")

    response = client.post(
        f"/tasks/{task_id}/move", data={"bucket": "today", "status": "todo"},
    )
    assert response.status_code == 204
    task = db_module.get_task(task_id)
    assert task["bucket"] == "today"
    assert task["status"] == "todo"


def test_move_rejects_unknown_bucket(client, db):
    task_id = db_module.create_task(title="A task")

    response = client.post(f"/tasks/{task_id}/move", data={"bucket": "someday"})
    assert response.status_code == 400
