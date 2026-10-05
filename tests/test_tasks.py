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


def test_today_view_includes_flagged_and_overdue(db):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    flagged_id = db_module.create_task(title="Flagged for today", is_today=True)
    overdue_id = db_module.create_task(title="Overdue", due_date=yesterday)
    db_module.create_task(title="Due in future, not flagged", due_date=tomorrow)

    titles = {t["title"] for t in db_module.list_today_view_tasks()}
    assert titles == {"Flagged for today", "Overdue"}


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
