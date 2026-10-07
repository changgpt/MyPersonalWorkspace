from datetime import date, timedelta

from daybook import db as db_module


def _make_note(body_markdown, event_date="2026-01-01"):
    note_type = db_module.list_note_types()[0]
    return db_module.create_note(
        title="Note", note_type_id=note_type["id"],
        event_date=event_date, body_markdown=body_markdown,
    )


def test_sync_creates_task_from_checkbox_line(db):
    note_id = _make_note("## Actions\n\n- [ ] Follow up on budget\n")
    db_module.sync_tasks_from_note(note_id, "## Actions\n\n- [ ] Follow up on budget\n")

    tasks = db_module.tasks_for_note(note_id)
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Follow up on budget"
    assert tasks[0]["status"] == "todo"


def test_resaving_note_does_not_duplicate_tasks(db):
    body = "- [ ] Follow up on budget\n"
    note_id = _make_note(body)
    db_module.sync_tasks_from_note(note_id, body)
    db_module.sync_tasks_from_note(note_id, body)  # simulate re-saving unchanged
    db_module.sync_tasks_from_note(note_id, body)

    assert len(db_module.tasks_for_note(note_id)) == 1


def test_adding_a_new_line_on_resave_only_creates_the_new_task(db):
    body_v1 = "- [ ] First item\n"
    note_id = _make_note(body_v1)
    db_module.sync_tasks_from_note(note_id, body_v1)

    body_v2 = "- [ ] First item\n- [ ] Second item\n"
    db_module.sync_tasks_from_note(note_id, body_v2)

    titles = {t["title"] for t in db_module.tasks_for_note(note_id)}
    assert titles == {"First item", "Second item"}


def test_completing_task_ticks_the_checkbox_in_the_note(db):
    body = "## Actions\n\n- [ ] Follow up on budget\n"
    note_id = _make_note(body)
    db_module.sync_tasks_from_note(note_id, body)
    task = db_module.tasks_for_note(note_id)[0]

    db_module.set_task_status(task["id"], "done")

    note = db_module.get_note(note_id)
    assert "- [x] Follow up on budget" in note["body_markdown"]
    assert "- [ ] Follow up on budget" not in note["body_markdown"]
    assert db_module.get_task(task["id"])["completed_at"] is not None


def test_sync_and_checkbox_toggle_work_with_crlf_line_endings(db):
    # The WYSIWYG note editor's HTML-to-Markdown conversion (Turndown)
    # joins blocks with \r\n, not \n -- extraction and the checkbox-sync
    # replace must not assume Unix line endings.
    body = "## Actions\r\n\r\n- [ ] Follow up on budget\r\n\r\n- [ ] Call the vendor"
    note_id = _make_note(body)
    db_module.sync_tasks_from_note(note_id, body)

    titles = {t["title"] for t in db_module.tasks_for_note(note_id)}
    assert titles == {"Follow up on budget", "Call the vendor"}

    task = next(t for t in db_module.tasks_for_note(note_id) if t["title"] == "Call the vendor")
    db_module.set_task_status(task["id"], "done")
    assert "- [x] Call the vendor" in db_module.get_note(note_id)["body_markdown"]


def test_reopening_task_unticks_the_checkbox(db):
    body = "- [ ] Follow up\n"
    note_id = _make_note(body)
    db_module.sync_tasks_from_note(note_id, body)
    task = db_module.tasks_for_note(note_id)[0]
    db_module.set_task_status(task["id"], "done")
    db_module.set_task_status(task["id"], "todo")

    note = db_module.get_note(note_id)
    assert "- [ ] Follow up" in note["body_markdown"]
    assert db_module.get_task(task["id"])["completed_at"] is None


def test_todo_style_line_has_no_checkbox_to_sync(db):
    body = "TODO: call the vendor\n"
    note_id = _make_note(body)
    db_module.sync_tasks_from_note(note_id, body)
    task = db_module.tasks_for_note(note_id)[0]

    db_module.set_task_status(task["id"], "done")  # should not raise, just no-ops on the note

    note = db_module.get_note(note_id)
    assert note["body_markdown"] == body
    assert db_module.get_task(task["id"])["status"] == "done"


def test_today_bucket_includes_flagged_and_overdue(db):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    db_module.create_task(title="Flagged for today", bucket="today")
    db_module.create_task(title="Overdue", bucket="background", due_date=yesterday)
    db_module.create_task(title="Due in future, not flagged", bucket="background", due_date=tomorrow)

    titles = {t["title"] for t in db_module.list_tasks_by_bucket("today")}
    assert titles == {"Flagged for today", "Overdue"}


def test_long_term_and_background_buckets_exclude_overdue_pull_forward(db):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    db_module.create_task(title="Overdue but long term", bucket="long_term", due_date=yesterday)
    db_module.create_task(title="Plain long term", bucket="long_term")
    db_module.create_task(title="Plain background", bucket="background")

    long_term_titles = {t["title"] for t in db_module.list_tasks_by_bucket("long_term")}
    assert long_term_titles == {"Overdue but long term", "Plain long term"}

    background_titles = {t["title"] for t in db_module.list_tasks_by_bucket("background")}
    assert background_titles == {"Plain background"}


def test_set_task_bucket_moves_a_task(db):
    task_id = db_module.create_task(title="Move me", bucket="today")
    db_module.set_task_bucket(task_id, "long_term")

    assert db_module.get_task(task_id)["bucket"] == "long_term"
    assert task_id not in {t["id"] for t in db_module.list_tasks_by_bucket("today")}
    assert task_id in {t["id"] for t in db_module.list_tasks_by_bucket("long_term")}


def test_overdue_excludes_done_tasks(db):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    task_id = db_module.create_task(title="Was overdue", due_date=yesterday)
    db_module.set_task_status(task_id, "done")

    assert db_module.list_overdue_tasks() == []


def test_completed_this_week(db):
    task_id = db_module.create_task(title="Done today")
    db_module.set_task_status(task_id, "done")

    titles = {t["title"] for t in db_module.list_tasks_completed_this_week()}
    assert "Done today" in titles


def test_list_tasks_filters_by_project_and_priority(db):
    project_id = db_module.find_or_create_project("Project X")
    db_module.create_task(title="High prio on project", priority="high", project_id=project_id)
    db_module.create_task(title="Low prio, no project", priority="low")

    results = db_module.list_tasks(project_id=project_id)
    assert [t["title"] for t in results] == ["High prio on project"]

    results = db_module.list_tasks(priority="low")
    assert [t["title"] for t in results] == ["Low prio, no project"]


def test_list_tasks_orders_by_priority_then_date(db):
    from datetime import date, timedelta
    today = date.today()

    db_module.create_task(title="Medium, no date", priority="medium")
    db_module.create_task(title="High, later", priority="high",
                           due_date=(today + timedelta(days=5)).isoformat())
    db_module.create_task(title="High, sooner", priority="high",
                           due_date=(today + timedelta(days=1)).isoformat())
    db_module.create_task(title="Low, with date", priority="low",
                           due_date=today.isoformat())

    titles = [t["title"] for t in db_module.list_tasks()]
    assert titles == ["High, sooner", "High, later", "Medium, no date", "Low, with date"]


def test_today_bucket_orders_by_priority_then_date(db):
    db_module.create_task(title="Low priority today", priority="low", bucket="today")
    db_module.create_task(title="High priority today", priority="high", bucket="today")
    db_module.create_task(title="Medium priority today", priority="medium", bucket="today")

    titles = [t["title"] for t in db_module.list_tasks_by_bucket("today")]
    assert titles == ["High priority today", "Medium priority today", "Low priority today"]
