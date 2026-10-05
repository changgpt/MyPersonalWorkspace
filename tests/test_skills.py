from daybook import db as db_module


def test_create_skill_records_initial_level_history(db):
    skill_id = db_module.create_skill("Negotiation", category="communication", level=2)
    history = db_module.skill_level_history(skill_id)
    assert len(history) == 1
    assert history[0]["level"] == 2


def test_find_or_create_skill_is_idempotent(db):
    id1 = db_module.find_or_create_skill("Excel modelling")
    id2 = db_module.find_or_create_skill("excel modelling")
    assert id1 == id2
    assert len(db_module.list_skills()) == 1


def test_update_skill_level_adds_history_entry_only_when_changed(db):
    skill_id = db_module.create_skill("SQL", level=1)
    db_module.update_skill(skill_id, name="SQL", category="technical", notes="", level=1)
    assert len(db_module.skill_level_history(skill_id)) == 1  # unchanged, no new entry

    db_module.update_skill(skill_id, name="SQL", category="technical", notes="", level=3)
    history = db_module.skill_level_history(skill_id)
    assert len(history) == 2
    assert history[-1]["level"] == 3
    assert db_module.get_skill(skill_id)["level"] == 3


def test_add_skill_evidence_and_fetch_for_entity(db):
    note_type = db_module.list_note_types()[0]
    note_id = db_module.create_note(
        title="Note", note_type_id=note_type["id"],
        event_date="2026-01-01", body_markdown="x",
    )
    db_module.add_skill_evidence("Public speaking", "note", note_id, comment="Ran the meeting")

    evidence = db_module.evidence_for_entity("note", note_id)
    assert len(evidence) == 1
    assert evidence[0]["skill_name"] == "Public speaking"
    assert evidence[0]["comment"] == "Ran the meeting"


def test_evidence_for_skill_resolves_entity_title(db):
    note_type = db_module.list_note_types()[0]
    note_id = db_module.create_note(
        title="Budget review", note_type_id=note_type["id"],
        event_date="2026-01-01", body_markdown="x",
    )
    db_module.add_skill_evidence("Financial modelling", "note", note_id)

    skill_id = db_module.find_or_create_skill("Financial modelling")
    evidence = db_module.evidence_for_skill(skill_id)
    assert evidence[0]["entity_title"] == "Budget review"
    assert evidence[0]["entity_type"] == "note"


def test_skills_touched_between_dates(db):
    skill_id = db_module.create_skill("Public speaking")
    task_id = db_module.create_task(title="Give a talk")
    db_module.add_skill_evidence("Public speaking", "task", task_id)

    import datetime
    today = datetime.date.today().isoformat()
    touched = db_module.skills_touched_between(today, today)
    assert {s["name"] for s in touched} == {"Public speaking"}

    touched_other_range = db_module.skills_touched_between("2000-01-01", "2000-01-02")
    assert touched_other_range == []
