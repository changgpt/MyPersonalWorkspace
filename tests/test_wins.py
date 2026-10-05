from daybook import db as db_module


def test_create_win_with_people(db):
    alice_id = db_module.find_or_create_person("Alice")
    win_id = db_module.create_win(
        win_date="2026-01-15", title="Shipped the migration",
        what_i_did="Led the cutover", impact_result="Zero downtime",
        person_ids=[alice_id],
    )
    win = db_module.get_win(win_id)
    assert win["title"] == "Shipped the migration"
    people = db_module.people_for_win(win_id)
    assert [p["name"] for p in people] == ["Alice"]


def test_update_win_replaces_people(db):
    alice_id = db_module.find_or_create_person("Alice")
    win_id = db_module.create_win(win_date="2026-01-15", title="Win", person_ids=[alice_id])

    bob_id = db_module.find_or_create_person("Bob")
    db_module.update_win(
        win_id, win_date="2026-01-16", title="Win (updated)",
        what_i_did="", impact_result="", project_id=None, person_ids=[bob_id],
    )
    people = db_module.people_for_win(win_id)
    assert [p["name"] for p in people] == ["Bob"]


def test_delete_win(db):
    win_id = db_module.create_win(win_date="2026-01-15", title="Temp")
    db_module.delete_win(win_id)
    assert db_module.get_win(win_id) is None


def test_list_wins_filters_by_project_and_date(db):
    project_id = db_module.find_or_create_project("Project X")
    db_module.create_win(win_date="2026-01-01", title="On project", project_id=project_id)
    db_module.create_win(win_date="2026-01-02", title="No project")

    assert [w["title"] for w in db_module.list_wins(project_id=project_id)] == ["On project"]
    assert [w["title"] for w in db_module.list_wins(date_from="2026-01-02")] == ["No project"]


def test_win_linked_to_source_task(db):
    task_id = db_module.create_task(title="Finish the report")
    db_module.set_task_status(task_id, "done")
    win_id = db_module.create_win(
        win_date="2026-01-15", title="Finished the report", source_task_id=task_id,
    )
    assert db_module.get_win(win_id)["source_task_id"] == task_id
