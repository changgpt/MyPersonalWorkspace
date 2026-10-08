from daybook import db as db_module


def _note(title, body="body"):
    note_type = db_module.list_note_types()[0]
    return db_module.create_note(
        title=title, note_type_id=note_type["id"], event_date="2026-01-01", body_markdown=body,
    )


def test_suggestions_span_every_kind_of_record(db):
    _note("FX hedging review")
    db_module.create_task(title="Review hedging exposure")
    db_module.find_or_create_person("Mia Hedges")
    db_module.find_or_create_project("Hedging Overlay")
    db_module.find_or_create_topic("FX hedging")

    groups = db_module.search_suggestions("hedg")
    assert [r["title"] for r in groups["notes"]] == ["FX hedging review"]
    assert [r["title"] for r in groups["tasks"]] == ["Review hedging exposure"]
    assert [r["name"] for r in groups["people"]] == ["Mia Hedges"]
    assert [r["name"] for r in groups["projects"]] == ["Hedging Overlay"]
    assert [r["name"] for r in groups["topics"]] == ["FX hedging"]


def test_suggestions_match_partial_words(db):
    _note("Quarterly valuations")
    db_module.find_or_create_project("Valuation Overhaul")

    groups = db_module.search_suggestions("valua")
    assert [r["title"] for r in groups["notes"]] == ["Quarterly valuations"]
    assert [r["name"] for r in groups["projects"]] == ["Valuation Overhaul"]


def test_blank_query_suggests_nothing(db):
    _note("Something")
    assert db_module.search_suggestions("") == {}
    assert db_module.search_suggestions("   ") == {}


def test_wildcards_typed_by_the_user_are_matched_literally(db):
    db_module.find_or_create_project("100% owned")
    db_module.find_or_create_project("Unrelated")

    # Without escaping, "%" is a LIKE wildcard: "100%" would match every
    # project, and a bare "%" would list all of them.
    assert [r["name"] for r in db_module.search_suggestions("100%")["projects"]] == ["100% owned"]
    assert [r["name"] for r in db_module.search_suggestions("%")["projects"]] == ["100% owned"]


def test_each_kind_is_capped(db):
    for i in range(9):
        db_module.find_or_create_person(f"Person {i}")

    assert len(db_module.search_suggestions("person")["people"]) == 5
    assert len(db_module.search_suggestions("person", limit_per_kind=2)["people"]) == 2


def test_suggest_endpoint_renders_matches_and_nothing_for_a_blank_query(client, db):
    _note("FX hedging review")

    body = client.get("/search/suggest?q=fx").get_data(as_text=True)
    assert "FX hedging review" in body
    assert "search-panel" in body

    assert client.get("/search/suggest?q=").get_data(as_text=True).strip() == ""


def test_suggest_endpoint_says_so_when_nothing_matches(client, db):
    _note("FX hedging review")
    body = client.get("/search/suggest?q=zzzz").get_data(as_text=True)
    assert "Nothing matches" in body


def test_results_page_back_link_points_at_where_the_search_came_from(client, db):
    body = client.get("/search?q=fx&from=/tasks").get_data(as_text=True)
    assert 'href="/tasks"' in body
    assert "Back to Tasks" in body

    # The search box sends request.full_path, which always ends in "?".
    body = client.get("/search?q=fx&from=/people?").get_data(as_text=True)
    assert 'href="/people"' in body

    body = client.get("/search?q=fx&from=/weekly-review/2026-W41").get_data(as_text=True)
    assert "Back to Weekly Review" in body


def test_back_link_falls_back_to_the_dashboard(client, db):
    for url in ("/search?q=fx", "/search?q=fx&from=https://evil.example.com"):
        body = client.get(url).get_data(as_text=True)
        assert "Back to Dashboard" in body
        assert "evil.example.com" not in body
