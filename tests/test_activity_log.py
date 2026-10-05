from daybook import db as db_module


def test_create_and_fetch_log_entry(db):
    log_id = db_module.create_log_entry(
        entry_date="2026-01-15", description="Reviewed budget", time_spent="30m",
    )
    entry = db_module.get_log_entry(log_id)
    assert entry["description"] == "Reviewed budget"
    assert entry["time_spent"] == "30m"


def test_update_and_delete_log_entry(db):
    log_id = db_module.create_log_entry(entry_date="2026-01-15", description="Original")
    db_module.update_log_entry(
        log_id, entry_date="2026-01-16", description="Updated",
        project_id=None, time_spent="1h",
    )
    assert db_module.get_log_entry(log_id)["description"] == "Updated"

    db_module.delete_log_entry(log_id)
    assert db_module.get_log_entry(log_id) is None


def test_activity_log_merges_all_sources_sorted_newest_first(db):
    note_type = db_module.list_note_types()[0]
    db_module.create_note(
        title="A note", note_type_id=note_type["id"],
        event_date="2026-01-01", body_markdown="x",
    )
    task_id = db_module.create_task(title="A task")
    db_module.set_task_status(task_id, "done")
    db_module.create_win(win_date="2099-01-01", title="A win")  # far future so it sorts first
    db_module.create_log_entry(entry_date="2000-01-01", description="An old log entry")

    items = db_module.list_activity()
    kinds = [item["kind"] for item in items]
    assert set(kinds) == {"note", "task", "win", "log_entry"}
    assert kinds[0] == "win"  # 2099 date sorts first
    assert kinds[-1] == "log_entry"  # 2000 date sorts last


def test_activity_log_filters_by_project(db):
    project_id = db_module.find_or_create_project("Project X")
    db_module.create_log_entry(entry_date="2026-01-01", description="On project", project_id=project_id)
    db_module.create_log_entry(entry_date="2026-01-02", description="No project")

    items = db_module.list_activity(project_id=project_id)
    assert [item["title"] for item in items] == ["On project"]


def test_activity_log_filters_by_date_range(db):
    db_module.create_log_entry(entry_date="2026-01-01", description="Too early")
    db_module.create_log_entry(entry_date="2026-06-01", description="In range")
    db_module.create_log_entry(entry_date="2026-12-01", description="Too late")

    items = db_module.list_activity(date_from="2026-02-01", date_to="2026-11-01")
    assert [item["title"] for item in items] == ["In range"]
