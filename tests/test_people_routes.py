from daybook import db as db_module


def test_update_person_saves_crm_fields(client, db):
    person_id = db_module.find_or_create_person("Alex Rivera")

    response = client.post(
        f"/people/{person_id}",
        data={
            "name": "Alex Rivera",
            "role": "Senior Analyst",
            "team": "Portfolio Ops",
            "how_met": "Introduced by my manager",
            "context": "Prefers async updates over meetings",
            "last_contacted_date": "2026-10-01",
            "follow_up": "Send the deck by Friday",
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"] == f"/people/{person_id}"

    person = db_module.get_person(person_id)
    assert person["role"] == "Senior Analyst"
    assert person["team"] == "Portfolio Ops"
    assert person["how_met"] == "Introduced by my manager"
    assert person["notes"] == "Prefers async updates over meetings"
    assert person["last_contacted_date"] == "2026-10-01"
    assert person["follow_up"] == "Send the deck by Friday"


def test_edit_view_renders_existing_values(client, db):
    person_id = db_module.find_or_create_person("Jordan Lee")
    db_module.update_person(
        person_id, name="Jordan Lee", role="PM", team="Platform",
        how_met="Conference", context="Loves hiking", last_contacted_date="2026-09-15",
        follow_up="Follow up re: roadmap",
    )

    response = client.get(f"/people/{person_id}/edit")
    body = response.get_data(as_text=True)
    assert "Jordan Lee" in body
    assert "Platform" in body
    assert "Loves hiking" in body
    assert "Follow up re: roadmap" in body


def test_update_view_404s_for_missing_person(client, db):
    response = client.post("/people/999", data={"name": "Ghost"})
    assert response.status_code == 404
