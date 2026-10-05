from datetime import date

from daybook import db as db_module


def test_current_week_str_format():
    week_str = db_module.current_week_str()
    year, week = week_str.split("-W")
    assert len(week) == 2
    assert int(year) == date.today().isocalendar()[0]


def test_week_str_to_monday_is_a_monday():
    monday = db_module.week_str_to_monday("2026-W03")
    assert monday.isoweekday() == 1
    assert monday.isocalendar()[:2] == (2026, 3)


def test_adjacent_week_str_moves_forward_and_back():
    assert db_module.adjacent_week_str("2026-W03", 1) == "2026-W04"
    assert db_module.adjacent_week_str("2026-W03", -1) == "2026-W02"


def test_adjacent_week_str_crosses_year_boundary_without_error():
    result = db_module.adjacent_week_str("2026-W01", -1)
    assert "-W" in result
    # going back then forward across the boundary returns to the start
    assert db_module.adjacent_week_str(result, 1) == "2026-W01"


def test_save_and_get_weekly_review_roundtrip(db):
    assert db_module.get_weekly_review("2026-W03") is None

    db_module.save_weekly_review(
        "2026-W03", went_well="Shipped X", to_improve="Fewer meetings",
        focus_next_week="Ship Y",
    )
    review = db_module.get_weekly_review("2026-W03")
    assert review["went_well"] == "Shipped X"

    db_module.save_weekly_review(
        "2026-W03", went_well="Updated", to_improve="", focus_next_week="",
    )
    assert db_module.get_weekly_review("2026-W03")["went_well"] == "Updated"


def test_weekly_review_summary_scopes_to_current_week(db):
    week_str = db_module.current_week_str()
    note_type = db_module.list_note_types()[0]
    db_module.create_note(
        title="This week's note", note_type_id=note_type["id"],
        event_date="2026-01-01", body_markdown="x",
    )

    done_task_id = db_module.create_task(title="Finish thing")
    db_module.set_task_status(done_task_id, "done")
    db_module.create_task(title="Still open")

    db_module.add_skill_evidence("Public speaking", "task", done_task_id)

    today = date.today().isoformat()
    db_module.create_win(win_date=today, title="This week's win")
    db_module.create_win(win_date="2000-01-01", title="Ancient win")

    summary = db_module.weekly_review_summary(week_str)

    assert summary["notes_by_type"][0]["count"] == 1
    assert [t["title"] for t in summary["tasks_completed"]] == ["Finish thing"]
    assert any(t["title"] == "Still open" for t in summary["tasks_open_or_overdue"])
    assert {s["name"] for s in summary["skills_touched"]} == {"Public speaking"}
    assert [w["title"] for w in summary["wins"]] == ["This week's win"]
