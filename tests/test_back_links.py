"""Every detail page offers a way back to its own list page.

Detail pages are reachable from several directions (a note from Notes, the
dashboard, a person, search...), so the back link points at the parent list
rather than the referrer -- these tests pin which list each page points at.
"""
from daybook import db as db_module


def _detail_urls():
    note_type_id = db_module.list_note_types()[0]["id"]
    note_id = db_module.create_note(
        "Weekly sync", note_type_id, "2026-10-07", "Body text",
        person_ids=[db_module.find_or_create_person("Alex Rivera")],
        project_ids=[db_module.find_or_create_project("Hedging model")],
        topic_ids=[db_module.find_or_create_topic("Risk")],
    )
    return [
        (f"/notes/{note_id}", "/notes", "Notes"),
        (f"/people/{db_module.find_or_create_person('Alex Rivera')}", "/people", "People"),
        (f"/projects/{db_module.find_or_create_project('Hedging model')}", "/projects", "Projects"),
        # Topics' list page is called "Knowledge Bank" in the nav, so the
        # back link says that rather than the route name.
        (f"/topics/{db_module.find_or_create_topic('Risk')}", "/topics", "Knowledge Bank"),
        (f"/wins/{db_module.create_win('2026-10-07', 'Shipped the model')}", "/wins", "Wins"),
        (f"/skills/{db_module.create_skill('Python')}", "/skills", "Skills"),
    ]


def test_every_detail_page_has_a_back_link_to_its_list(client, app):
    with app.app_context():
        urls = _detail_urls()

    for detail_url, list_url, label in urls:
        response = client.get(detail_url)
        assert response.status_code == 200, detail_url
        body = response.get_data(as_text=True)
        assert f'class="back-link" href="{list_url}"' in body, detail_url
        assert label in body, detail_url
