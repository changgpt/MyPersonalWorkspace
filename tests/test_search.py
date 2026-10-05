from daybook import db as db_module


def test_search_finds_match_in_title_and_body(db):
    note_type = db_module.list_note_types()[0]
    db_module.create_note(
        title="Quarterly planning",
        note_type_id=note_type["id"],
        event_date="2026-01-01",
        body_markdown="We discussed the budget for next quarter.",
    )
    db_module.create_note(
        title="Unrelated note",
        note_type_id=note_type["id"],
        event_date="2026-01-02",
        body_markdown="Nothing to do with it.",
    )

    results = db_module.search_notes("budget")
    assert len(results) == 1
    assert "<mark>budget</mark>" in results[0]["snippet_html"]

    title_results = db_module.search_notes("Quarterly")
    assert len(title_results) == 1
    assert "<mark>Quarterly</mark>" in title_results[0]["title_html"]


def test_search_empty_query_returns_nothing(db):
    assert db_module.search_notes("") == []
    assert db_module.search_notes("   ") == []


def test_search_no_matches(db):
    note_type = db_module.list_note_types()[0]
    db_module.create_note(
        title="Something", note_type_id=note_type["id"],
        event_date="2026-01-01", body_markdown="text",
    )
    assert db_module.search_notes("zzzznomatch") == []


def test_search_index_updates_after_edit(db):
    note_type = db_module.list_note_types()[0]
    note_id = db_module.create_note(
        title="Original title", note_type_id=note_type["id"],
        event_date="2026-01-01", body_markdown="original body",
    )
    assert len(db_module.search_notes("original")) == 1

    db_module.update_note(
        note_id, title="Renamed title", note_type_id=note_type["id"],
        event_date="2026-01-01", body_markdown="changed body",
    )
    assert db_module.search_notes("original") == []
    assert len(db_module.search_notes("changed")) == 1


def test_search_index_updates_after_delete(db):
    note_type = db_module.list_note_types()[0]
    note_id = db_module.create_note(
        title="To be deleted", note_type_id=note_type["id"],
        event_date="2026-01-01", body_markdown="gone soon",
    )
    db_module.delete_note(note_id)
    assert db_module.search_notes("deleted") == []
