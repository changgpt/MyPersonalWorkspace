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
