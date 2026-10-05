from daybook.task_extraction import extract_action_items


def test_extracts_checkbox_line():
    assert extract_action_items("- [ ] Follow up with finance") == ["Follow up with finance"]


def test_extracts_todo_line_case_insensitive():
    assert extract_action_items("todo: email Jamie") == ["email Jamie"]
    assert extract_action_items("TODO: email Jamie") == ["email Jamie"]


def test_ignores_checked_checkbox():
    assert extract_action_items("- [x] Already done") == []


def test_ignores_plain_text_and_bullets():
    text = "Just a sentence.\n- A plain bullet, no checkbox\n## Heading"
    assert extract_action_items(text) == []


def test_extracts_multiple_lines_in_order():
    text = (
        "## Actions\n"
        "- [ ] First thing\n"
        "- [ ] Second thing\n"
        "TODO: a third thing\n"
    )
    assert extract_action_items(text) == ["First thing", "Second thing", "a third thing"]


def test_empty_body():
    assert extract_action_items("") == []
    assert extract_action_items(None) == []
