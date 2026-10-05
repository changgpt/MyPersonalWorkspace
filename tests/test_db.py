from daybook import db as db_module


def test_seeded_note_types(db):
    types = db_module.list_note_types()
    names = {row["name"] for row in types}
    assert "Meeting note" in names
    assert "Idea" in names
    assert len(types) == 7


def test_create_note_with_tags(db):
    note_type = db_module.list_note_types()[0]
    note_id = db_module.create_note(
        title="Test note",
        note_type_id=note_type["id"],
        event_date="2026-01-15",
        body_markdown="Hello world",
        person_ids=[db_module.find_or_create_person("Alice")],
        project_ids=[db_module.find_or_create_project("Project A")],
        topic_ids=[db_module.find_or_create_topic("Onboarding")],
    )
    note = db_module.get_note(note_id)
    assert note["title"] == "Test note"

    tags = db_module.get_note_tags(note_id)
    assert [p["name"] for p in tags["people"]] == ["Alice"]
    assert [p["name"] for p in tags["projects"]] == ["Project A"]
    assert [t["name"] for t in tags["topics"]] == ["Onboarding"]


def test_find_or_create_is_case_insensitive_and_idempotent(db):
    id1 = db_module.find_or_create_person("Bob Smith")
    id2 = db_module.find_or_create_person("bob smith")
    assert id1 == id2
    assert len(db_module.list_people()) == 1


def test_update_note_replaces_tags(db):
    note_type = db_module.list_note_types()[0]
    note_id = db_module.create_note(
        title="Note",
        note_type_id=note_type["id"],
        event_date="2026-01-15",
        body_markdown="body",
        person_ids=[db_module.find_or_create_person("Alice")],
    )
    db_module.update_note(
        note_id,
        title="Note",
        note_type_id=note_type["id"],
        event_date="2026-01-15",
        body_markdown="body",
        person_ids=[db_module.find_or_create_person("Carol")],
    )
    tags = db_module.get_note_tags(note_id)
    assert [p["name"] for p in tags["people"]] == ["Carol"]


def test_delete_note_removes_it(db):
    note_type = db_module.list_note_types()[0]
    note_id = db_module.create_note(
        title="Temp", note_type_id=note_type["id"],
        event_date="2026-01-15", body_markdown="x",
    )
    db_module.delete_note(note_id)
    assert db_module.get_note(note_id) is None


def test_list_notes_filters_by_person(db):
    note_type = db_module.list_note_types()[0]
    alice_id = db_module.find_or_create_person("Alice")
    db_module.find_or_create_person("Dana")
    db_module.create_note(
        title="With Alice", note_type_id=note_type["id"],
        event_date="2026-01-01", body_markdown="x", person_ids=[alice_id],
    )
    db_module.create_note(
        title="Without Alice", note_type_id=note_type["id"],
        event_date="2026-01-02", body_markdown="x",
    )
    results = db_module.list_notes(person_id=alice_id)
    assert [n["title"] for n in results] == ["With Alice"]


def test_list_notes_sorted_newest_first(db):
    note_type = db_module.list_note_types()[0]
    db_module.create_note(
        title="Older", note_type_id=note_type["id"],
        event_date="2026-01-01", body_markdown="x",
    )
    db_module.create_note(
        title="Newer", note_type_id=note_type["id"],
        event_date="2026-02-01", body_markdown="x",
    )
    results = db_module.list_notes()
    assert [n["title"] for n in results] == ["Newer", "Older"]


def test_archive_note_type_excluded_by_default(db):
    note_type = db_module.list_note_types()[0]
    db_module.set_note_type_active(note_type["id"], is_active=False)
    active = {nt["id"] for nt in db_module.list_note_types()}
    all_types = {nt["id"] for nt in db_module.list_note_types(include_archived=True)}
    assert note_type["id"] not in active
    assert note_type["id"] in all_types
