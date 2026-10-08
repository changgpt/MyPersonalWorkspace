from daybook.markdown_utils import render_markdown


def test_renders_heading():
    html = render_markdown("## Discussion")
    assert "<h2>Discussion</h2>" in html


def test_renders_bold_and_italic():
    html = render_markdown("**bold** and *italic*")
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html


def test_renders_task_list_checkbox():
    html = render_markdown("- [ ] Follow up\n- [x] Done already")
    assert "task-list-item" in html
    assert "checked" in html  # the completed item's checkbox is checked


def test_empty_body_renders_without_error():
    assert render_markdown("") == ""
    assert render_markdown(None) == ""


def test_single_line_breaks_are_preserved():
    html = render_markdown("Line one\nLine two\nLine three")
    assert html.count("<br") == 2


def test_blank_line_still_starts_a_new_paragraph():
    html = render_markdown("Paragraph one\n\nParagraph two")
    assert html.count("<p>") == 2
    assert "<br" not in html


def test_renders_strikethrough():
    html = render_markdown("~~dropped~~ from scope")
    assert "<del>dropped</del>" in html


def test_single_tilde_is_left_alone():
    # Subscript is switched off on purpose (see markdown_utils): a lone "~"
    # is ordinary punctuation in a note, not markup.
    html = render_markdown("approx ~20 people")
    assert "<sub>" not in html
    assert "~20" in html


def test_renders_blockquote_and_inline_code():
    html = render_markdown("> quoted line")
    assert "<blockquote>" in html
    assert "<code>db.py</code>" in render_markdown("see `db.py`")
