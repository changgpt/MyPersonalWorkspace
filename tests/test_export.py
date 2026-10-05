from daybook import db as db_module


def test_export_includes_note_with_resolved_tags(db):
    note_type = db_module.list_note_types()[0]
    person_id = db_module.find_or_create_person("Alice")
    project_id = db_module.find_or_create_project("Project X")
    topic_id = db_module.find_or_create_topic("Budgeting")
    db_module.create_note(
        title="Vendor call", note_type_id=note_type["id"],
        event_date="2026-01-01", body_markdown="Discussed terms.",
        person_ids=[person_id], project_ids=[project_id], topic_ids=[topic_id],
    )

    data = db_module.export_all_data()
    assert len(data["notes"]) == 1
    note = data["notes"][0]
    assert note["title"] == "Vendor call"
    assert note["type_name"] == note_type["name"]
    assert note["people"] == ["Alice"]
    assert note["projects"] == ["Project X"]
    assert note["topics"] == ["Budgeting"]


def test_export_includes_win_with_resolved_people(db):
    person_id = db_module.find_or_create_person("Bob")
    db_module.create_win(win_date="2026-01-15", title="Shipped it", person_ids=[person_id])

    data = db_module.export_all_data()
    assert len(data["wins"]) == 1
    assert data["wins"][0]["people"] == ["Bob"]


def test_export_includes_tasks_skills_log_entries(db):
    db_module.create_task(title="A task")
    db_module.create_skill("A skill")
    db_module.create_log_entry(entry_date="2026-01-01", description="Did a thing")

    data = db_module.export_all_data()
    assert [t["title"] for t in data["tasks"]] == ["A task"]
    assert [s["name"] for s in data["skills"]] == ["A skill"]
    assert [l["description"] for l in data["log_entries"]] == ["Did a thing"]


def test_export_is_json_serializable(db):
    import json

    db_module.create_task(title="A task")
    data = db_module.export_all_data()
    json.dumps(data)  # should not raise


def test_backup_db_command_copies_the_sqlite_file(app):
    with app.app_context():
        result = app.test_cli_runner().invoke(args=["backup-db"])
    assert result.exit_code == 0, result.output

    backups_dir = app.config["DATABASE_PATH"].parent / "backups"
    backups = list(backups_dir.glob("daybook-*.db"))
    assert len(backups) == 1
